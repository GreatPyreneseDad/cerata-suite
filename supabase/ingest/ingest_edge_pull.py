#!/usr/bin/env python3
"""
cerata → Supabase ingest.

Reads the cached EdgeOS attendance pull (and, optionally, a previously built
forecast-data.js for its upcoming-events list), runs Louvain on niche
co-attendance (same math as panel/build_forecast.py), then emits idempotent
SQL chunks for the `cerata` schema.

Privacy is structural, not procedural: legal names NEVER appear in the output.
Each person becomes sha256(salt || profile_id) plus a deterministic pseudonym
minted from that hash. The salt lives next to this script (gitignored) so
re-ingests upsert onto the same rows; without it the hashes are irreversible.

Usage:
  python3 ingest_edge_pull.py [--pull /tmp/edge_pull.json] \
                              [--forecast path/to/forecast-data.js] \
                              [--out /tmp/cerata_sql]
  # then:  for f in /tmp/cerata_sql/*.sql; do psql "$SUPABASE_DB_URL" -f "$f"; done
"""
import argparse, hashlib, json, math, os, secrets
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))

ADJ = ["amber","ashen","blue","bold","briar","bright","calm","cedar","civic","clear",
       "coral","dapper","dawn","deep","dusk","eager","early","ember","fable","fern",
       "flint","gentle","gilded","glass","green","hazel","hidden","indigo","iron","ivory",
       "jade","keen","late","lunar","mellow","misty","noble","north","ochre","opal",
       "pale","quiet","rose","rust","sable","salt","silver","slate","still","storm",
       "swift","tidal","umber","velvet","violet","warm","wild","winter","woven","zephyr"]
CREATURE = ["heron","otter","fox","wren","lynx","seal","crane","finch","badger","ibis",
            "marten","osprey","plover","raven","sable","tern","vole","walrus","egret","stoat",
            "curlew","dipper","ermine","fulmar","gannet","godwit","grebe","jay","kite","knot",
            "lapwing","loon","merlin","murre","newt","oriole","pika","pipit","puffin","quail",
            "redstart","sanderling","shrike","siskin","skua","smew","snipe","swift","teal","thrush"]

def alias_for(h, taken):
    n = int(h[:12], 16)
    for bump in range(64):
        a = ADJ[(n + bump * 7) % len(ADJ)]
        c = CREATURE[(n // len(ADJ) + bump * 13) % len(CREATURE)]
        cand = f"{a}-{c}"
        if cand not in taken:
            taken.add(cand)
            return cand
    cand = f"{ADJ[n % len(ADJ)]}-{CREATURE[n % len(CREATURE)]}-{h[:4]}"
    taken.add(cand)
    return cand

def q(s):
    if s is None:
        return "null"
    return "'" + str(s).replace("'", "''") + "'"

def qt(s):
    return q(s) if s else "null"

def qarr(tags):
    if not tags:
        return "'{}'"
    inner = ",".join('"' + str(t).replace('\\', '\\\\').replace('"', '\\"') + '"' for t in tags)
    return "'{" + inner.replace("'", "''") + "}'"

def louvain(attend, csize, lo=3, hi=25):
    """Same clustering as panel/build_forecast.py — niche co-attendance, log-damped."""
    niche = {eid for eid, n in csize.items() if lo <= n <= hi}
    mset = {p: (attend[p] & niche) for p in attend}
    mset = {p: s for p, s in mset.items() if len(s) >= 2}
    ev_people = defaultdict(list)
    for p, s in mset.items():
        for eid in s:
            ev_people[eid].append(p)
    shared_w, shared_n = defaultdict(float), defaultdict(int)
    for eid, plist in ev_people.items():
        ww = 1.0 / math.log(2 + csize[eid])
        for i in range(len(plist)):
            for j in range(i + 1, len(plist)):
                k = (plist[i], plist[j]) if plist[i] < plist[j] else (plist[j], plist[i])
                shared_w[k] += ww; shared_n[k] += 1
    adj = defaultdict(dict)
    for (a, b), n in shared_n.items():
        if n >= 2:
            adj[a][b] = shared_w[(a, b)]; adj[b][a] = shared_w[(a, b)]
    nodes = [p for p in mset if p in adj and adj[p]]
    k = {u: sum(adj[u].values()) for u in nodes}
    m = sum(k.values()) / 2.0 or 1.0
    comm = {u: u for u in nodes}
    Sig = {u: k[u] for u in nodes}
    improved, passes = True, 0
    while improved and passes < 40:
        improved, passes = False, passes + 1
        for u in sorted(nodes, key=lambda x: -k[x]):
            cu = comm[u]
            wc = defaultdict(float)
            for v, wt in adj[u].items():
                wc[comm[v]] += wt
            Sig[cu] -= k[u]
            best, bestgain = cu, wc.get(cu, 0.0) - Sig[cu] * k[u] / (2 * m)
            for c, kin in wc.items():
                g = kin - Sig[c] * k[u] / (2 * m)
                if g > bestgain:
                    bestgain, best = g, c
            comm[u] = best; Sig[best] += k[u]
            if best != cu:
                improved = True
    groups = defaultdict(list)
    for u in nodes:
        groups[comm[u]].append(u)
    cohort_list = sorted([g for g in groups.values() if len(g) >= 4], key=len, reverse=True)
    Q = sum((adj[u].get(v, 0) - k[u] * k[v] / (2 * m))
            for u in nodes for v in adj[u] if comm[u] == comm[v]) / (2 * m)
    return cohort_list, mset, round(Q, 3)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pull", default="/tmp/edge_pull.json")
    ap.add_argument("--forecast", default=None, help="optional forecast-data.js for upcoming events")
    ap.add_argument("--out", default="/tmp/cerata_sql")
    ap.add_argument("--chunk", type=int, default=400)
    args = ap.parse_args()

    salt_path = os.path.join(HERE, ".salt")
    if os.path.exists(salt_path):
        salt = open(salt_path).read().strip()
    else:
        salt = secrets.token_hex(16)
        open(salt_path, "w").write(salt)
        print(f"minted new salt -> {salt_path} (gitignored; keep it to make re-ingests idempotent)")

    blob = json.load(open(args.pull))
    uniq, rosters = blob["uniq"], blob["rosters"]

    attend = defaultdict(set)
    rows_by_pair = {}
    for eid, rows in rosters.items():
        for r in rows:
            pid = r.get("profile_id")
            if not pid:
                continue
            attend[pid].add(eid)
            key = (pid, eid)
            prev = rows_by_pair.get(key)
            reg = r.get("registered_at")
            chk = r.get("check_time")
            status = r.get("status")
            if prev is None:
                rows_by_pair[key] = {"reg": reg, "chk": chk, "status": status}
            else:
                if reg and (not prev["reg"] or reg < prev["reg"]):
                    prev["reg"] = reg
                if chk and not prev["chk"]:
                    prev["chk"] = chk
    csize = {eid: len(set(r.get("profile_id") for r in rows if r.get("profile_id")))
             for eid, rows in rosters.items()}

    taken = set()
    hash_of, alias_of = {}, {}
    for pid in sorted(attend):
        h = hashlib.sha256((salt + pid).encode()).hexdigest()
        hash_of[pid] = h
        alias_of[pid] = alias_for(h, taken)

    cohort_list, mset, Q = louvain(attend, csize)

    def emeta(eid):
        e = uniq.get(eid, {})
        return {"title": e.get("title"), "track": e.get("track_title"),
                "host": e.get("host_display_name") or "", "tags": e.get("tags") or [],
                "start": e.get("start_time"), "end": e.get("end_time")}

    labels = []
    for g in cohort_list:
        tracks, tags = Counter(), Counter()
        for p in g:
            for eid in mset[p]:
                mm = emeta(eid)
                if mm["track"]: tracks[mm["track"]] += 1
                for t in mm["tags"]: tags[t] += 1
        label = (tags.most_common(1)[0][0] if tags else "cohort") + " · " + \
                (tracks.most_common(1)[0][0] if tracks else "")
        labels.append(label.strip(" ·"))

    upcoming = []
    if args.forecast and os.path.exists(args.forecast):
        s = open(args.forecast).read()
        d = json.loads(s[s.index("=") + 1:].rstrip().rstrip(";"))
        upcoming = (d.get("market") or {}).get("upcoming") or []

    os.makedirs(args.out, exist_ok=True)
    nfile = 0
    def emit(sql, label):
        nonlocal nfile
        nfile += 1
        path = os.path.join(args.out, f"{nfile:02d}_{label}.sql")
        open(path, "w").write(sql)
        print(f"wrote {path} ({len(sql)//1024} KB)")

    people_vals = ",\n".join(f"({q(hash_of[p])}, {q(alias_of[p])})" for p in sorted(attend))
    emit("insert into cerata.people (ext_hash, alias) values\n" + people_vals +
         "\non conflict (ext_hash) do nothing;\n", "people")

    ev_rows = []
    for eid in uniq:
        mm = emeta(eid)
        ev_rows.append(f"({q(eid)}, {q(mm['title'] or 'untitled')}, {qt(mm['track'])}, "
                       f"{qt(mm['host'])}, {qarr(mm['tags'])}, {qt(mm['start'])}, {qt(mm['end'])})")
    seen_up = set(uniq)
    for e in upcoming:
        if not e.get("id") or e["id"] in seen_up:
            continue
        seen_up.add(e["id"])
        ev_rows.append(f"({q(e['id'])}, {q(e.get('title') or 'untitled')}, {qt(e.get('track'))}, "
                       f"{qt(e.get('host'))}, {qarr(e.get('tags'))}, {qt(e.get('start'))}, {qt(e.get('end'))})")
    for i in range(0, len(ev_rows), args.chunk):
        emit("insert into cerata.events (ext_id, title, track, host, tags, starts_at, ends_at) values\n"
             + ",\n".join(ev_rows[i:i + args.chunk])
             + "\non conflict (ext_id) do update set title = excluded.title, track = excluded.track, "
               "host = excluded.host, tags = excluded.tags, starts_at = excluded.starts_at, "
               "ends_at = excluded.ends_at;\n", f"events_{i//args.chunk}")

    att_rows = []
    for (pid, eid), v in sorted(rows_by_pair.items()):
        prov = "checkin" if v["chk"] else "rsvp"
        att_rows.append(f"({q(hash_of[pid])}, {q(eid)}, {q(prov)}, {qt(v['status'])}, "
                        f"{qt(v['reg'])}, {qt(v['chk'])})")
    for i in range(0, len(att_rows), args.chunk):
        emit("insert into cerata.attendance (person_id, event_id, provenance, rsvp_status, registered_at, checked_in_at)\n"
             "select p.id, e.id, v.prov::cerata.provenance, v.status, v.reg::timestamptz, v.chk::timestamptz\n"
             "from (values\n" + ",\n".join(att_rows[i:i + args.chunk]) + "\n"
             ") as v(ext_hash, ext_id, prov, status, reg, chk)\n"
             "join cerata.people p on p.ext_hash = v.ext_hash\n"
             "join cerata.events e on e.ext_id = v.ext_id\n"
             "on conflict (person_id, event_id) do update set provenance = excluded.provenance, "
             "checked_in_at = excluded.checked_in_at;\n", f"attendance_{i//args.chunk}")

    cohort_vals = ",\n".join(f"({i}, {q(labels[i])})" for i in range(len(cohort_list)))
    member_vals = ",\n".join(f"({i}, {q(hash_of[p])})"
                             for i, g in enumerate(cohort_list) for p in g)
    emit(
        "update cerata.cohort_runs set is_current = false where is_current;\n"
        "with run as (\n"
        f"  insert into cerata.cohort_runs (algorithm, params, modularity, is_current)\n"
        f"  values ('louvain-niche', '{{\"lo\":3,\"hi\":25,\"min_cohort\":4}}'::jsonb, {Q}, true)\n"
        "  returning id\n"
        "), cs as (\n"
        "  insert into cerata.cohorts (run_id, idx, label)\n"
        f"  select run.id, v.idx, v.label from run, (values\n{cohort_vals}\n) as v(idx, label)\n"
        "  returning id, idx\n"
        ")\n"
        "insert into cerata.cohort_members (cohort_id, person_id)\n"
        f"select cs.id, p.id from cs\n"
        f"join (values\n{member_vals}\n) as m(idx, ext_hash) on m.idx = cs.idx\n"
        "join cerata.people p on p.ext_hash = m.ext_hash;\n", "cohorts")

    print(f"\npeople={len(attend)} events={len(ev_rows)} attendance={len(att_rows)} "
          f"cohorts={len(cohort_list)} modularity={Q}")
    print("apply in order:  for f in " + args.out + "/*.sql; do psql \"$SUPABASE_DB_URL\" -f \"$f\"; done")

if __name__ == "__main__":
    main()
