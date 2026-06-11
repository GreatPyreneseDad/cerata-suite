#!/usr/bin/env python3
"""
Cerata Panel — forecast data builder.
Turns the cached EdgeOS attendance pull into per-class and per-person "reads":
cohorts (Louvain), co-attendance, cohort-affinity predictions, and an
RSVP/reattendance-based enjoyment proxy. Emits forecast-data.js (window.FORECAST)
so the panel opens by double-click with no server.

Input : /tmp/edge_pull.json   (events + rosters, from attendance_extract.py)
Output: ./forecast-data.js
"""
import json, math, os
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PULL = "/tmp/edge_pull.json"
blob = json.load(open(PULL))
uniq, rosters = blob["uniq"], blob["rosters"]

# ---- matrix ----
attend = defaultdict(set); name = {}
for eid, rows in rosters.items():
    for r in rows:
        pid = r.get("profile_id")
        if not pid:
            continue
        attend[pid].add(eid)
        nm = ((r.get("first_name") or "").strip() + " " + (r.get("last_name") or "").strip()).strip()
        if nm:
            name[pid] = nm
csize = {eid: len(set(r.get("profile_id") for r in rows if r.get("profile_id"))) for eid, rows in rosters.items()}
total_rows = sum(len(r) for r in rosters.values())
checkins = sum(1 for rows in rosters.values() for r in rows if r.get("check_time"))

def meta(eid):
    e = uniq.get(eid, {})
    return {"title": e.get("title"), "track": e.get("track_title"),
            "host": e.get("host_display_name") or "", "tags": e.get("tags") or [],
            "start": e.get("start_time"), "end": e.get("end_time")}

# ---- Louvain cohorts on niche co-attendance (same as cohort_v3) ----
LO, HI = 3, 25
niche = {eid for eid, n in csize.items() if LO <= n <= HI}
mset = {p: (attend[p] & niche) for p in attend}
mset = {p: s for p, s in mset.items() if len(s) >= 2}
ev_people = defaultdict(list)
for p, s in mset.items():
    for eid in s:
        ev_people[eid].append(p)
def w(eid): return 1.0 / math.log(2 + csize[eid])
shared_w = defaultdict(float); shared_n = defaultdict(int)
for eid, plist in ev_people.items():
    ww = w(eid)
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
person_cohort = {}
cohorts = []
for i, g in enumerate(cohort_list):
    tracks, tags, hosts, titles = Counter(), Counter(), Counter(), Counter()
    for p in g:
        person_cohort[p] = i
        for eid in mset[p]:
            mm = meta(eid)
            if mm["track"]: tracks[mm["track"]] += 1
            for t in mm["tags"]: tags[t] += 1
            if mm["host"]: hosts[mm["host"]] += 1
            if mm["title"]: titles[mm["title"]] += 1
    label = (tags.most_common(1)[0][0] if tags else "cohort") + " · " + (tracks.most_common(1)[0][0] if tracks else "")
    cohorts.append({
        "id": i, "label": label.strip(" ·"), "size": len(g),
        "tags": tags.most_common(5), "tracks": tracks.most_common(3), "hosts": hosts.most_common(3),
        "signature_classes": [t for t, _ in titles.most_common(6)],
        "members": [name.get(p, p[:8]) for p in sorted(g, key=lambda p: -len(mset[p]))[:10]],
    })

# cohort class-profile: for each cohort, count of members attending each class
cohort_class = defaultdict(lambda: Counter())
for p, ci in person_cohort.items():
    for eid in attend[p]:
        cohort_class[ci][eid] += 1

# ---- per-class reads ----
def host_track_return(eid):
    """enjoyment proxy: of this class's attendees, fraction who ALSO attended
    another class by the same host / same track (cohort stuck with it)."""
    mm = meta(eid); host, track = mm["host"], mm["track"]
    atts = [r.get("profile_id") for r in rosters.get(eid, []) if r.get("profile_id")]
    atts = list(set(atts))
    if not atts:
        return {"host_return": None, "track_return": None}
    def ret(key, val):
        if not val:
            return None
        hit = 0
        for p in atts:
            for e2 in attend[p]:
                if e2 != eid and meta(e2)[key] == val:
                    hit += 1; break
        return round(hit / len(atts), 3)
    return {"host_return": ret("host", host), "track_return": ret("track", track)}

classes = []
for eid in uniq:
    mm = meta(eid)
    mix = Counter()
    for r in rosters.get(eid, []):
        p = r.get("profile_id")
        if p in person_cohort:
            mix[person_cohort[p]] += 1
    # predicted attendees: members of the dominant cohorts who attend this host/track a lot
    enj = host_track_return(eid)
    classes.append({
        "id": eid, "title": mm["title"], "track": mm["track"], "host": mm["host"],
        "tags": mm["tags"], "start": mm["start"], "end": mm["end"], "attendee_count": csize.get(eid, 0),
        "cohort_mix": [[ci, c] for ci, c in mix.most_common()],
        "attendees": [name.get(r.get("profile_id"), "") for r in rosters.get(eid, [])
                      if r.get("profile_id") and name.get(r.get("profile_id"))][:60],
        "enjoyment": enj,
    })

# ---- per-person reads ----
# co-attendance (niche-weighted) per person
coatt = defaultdict(Counter)
for (a, b), n in shared_n.items():
    coatt[a][b] += n; coatt[b][a] += n
people = []
for p in attend:
    ci = person_cohort.get(p)
    my_classes = attend[p]
    # predicted next classes: classes cohort-mates attend that p hasn't, ranked by cohortmate count
    pred = []
    if ci is not None:
        for eid, cnt in cohort_class[ci].most_common():
            if eid not in my_classes and csize.get(eid, 0) <= 60:  # skip mega-communal
                pred.append([meta(eid)["title"], cnt])
            if len(pred) >= 8:
                break
    sig_tracks, sig_tags, sig_hosts = Counter(), Counter(), Counter()
    for eid in my_classes:
        mm = meta(eid)
        if mm["track"]: sig_tracks[mm["track"]] += 1
        for t in mm["tags"]: sig_tags[t] += 1
        if mm["host"]: sig_hosts[mm["host"]] += 1
    people.append({
        "id": p, "name": name.get(p, p[:8]), "cohort_id": ci, "n_classes": len(my_classes),
        "classes": [meta(e)["title"] for e in sorted(my_classes, key=lambda e: csize.get(e, 0))][:40],
        "co_attendees": [[name.get(q, q[:8]), c] for q, c in coatt[p].most_common(8) if name.get(q)],
        "predicted_classes": pred,
        "signature": {"tracks": sig_tracks.most_common(3), "tags": sig_tags.most_common(4),
                      "hosts": sig_hosts.most_common(3)},
    })
people.sort(key=lambda x: -x["n_classes"])

# ---- cohort affinity: propensity over track / host / tag from PAST attendance ----
cohort_aff = {}
for ci, members in enumerate(cohort_list):
    tr, ho, tg = Counter(), Counter(), Counter(); tot = 0
    for p in members:
        for eid in attend[p]:
            mm = meta(eid); tot += 1
            if mm["track"]: tr[mm["track"]] += 1
            if mm["host"]: ho[mm["host"]] += 1
            for t in mm["tags"]: tg[t] += 1
    tot = tot or 1
    cohort_aff[ci] = {
        "track": {k: round(v / tot, 4) for k, v in tr.items()},
        "host": {k: round(v / tot, 4) for k, v in ho.items()},
        "tag": {k: round(v / tot, 4) for k, v in tg.items()},
    }

# ---- live pull of UPCOMING events for the allocation market ----
import urllib.request, urllib.parse
KEY = os.environ.get("EDGEOS_API_KEY", "")  # export EDGEOS_API_KEY=eos_live_...
POPUP = "43746fd0-bce2-472b-93e4-a438177b2dff"
BASE = "https://api.edgeos.world/api/v1"
NOW = os.environ.get("MARKET_NOW", "2026-06-11T07:00:00Z")
def _ev(params):
    try:
        req = urllib.request.Request(BASE + "/events/portal/events?" + urllib.parse.urlencode(params),
                                     headers={"Authorization": "Bearer " + KEY})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except Exception as e:
        print("upcoming pull failed:", e); return {}
raw, skip = [], 0
while True:
    d = _ev({"popup_id": POPUP, "event_status": "published", "start_after": NOW,
             "start_before": "2026-06-28T07:00:00Z", "limit": 100, "skip": skip})
    res = (d or {}).get("results", [])
    raw += res
    if len(res) < 100: break
    skip += 100
seen, upcoming = set(), []
for e in raw:
    key = (e.get("id"), e.get("start_time"))
    if key in seen: continue
    seen.add(key)
    upcoming.append({"id": e.get("id"), "title": e.get("title"), "track": e.get("track_title"),
                     "host": e.get("host_display_name") or "", "tags": e.get("tags") or [],
                     "start": e.get("start_time"), "end": e.get("end_time")})
market = {"now": NOW, "upcoming": upcoming, "cohort_aff": cohort_aff}
print(f"upcoming events for market: {len(upcoming)}")

data = {
    "meta": {
        "people": len(attend), "classes": len(uniq), "cohorts": len(cohorts),
        "modularity": round(sum(
            (adj[u].get(v, 0) - k[u] * k[v] / (2 * m))
            for u in nodes for v in adj[u] if comm[u] == comm[v]) / (2 * m), 3),
        "checkin_coverage": round(checkins / total_rows, 4) if total_rows else 0,
        "avg_classes": round(sum(len(s) for s in attend.values()) / len(attend), 2),
        "roster_rows": total_rows,
        "note": "RSVP data (check-in coverage ~0.2%). Predicts who SIGNS UP; enjoyment = cohort reattendance to host/track, not confirmed presence.",
    },
    "cohorts": cohorts,
    "classes": classes,
    "people": people,
    "market": market,
}
out = os.path.join(HERE, "forecast-data.js")
with open(out, "w") as f:
    f.write("window.FORECAST = " + json.dumps(data, default=str) + ";\n")
print(f"people={len(attend)} classes={len(uniq)} cohorts={len(cohorts)} -> {out} ({os.path.getsize(out)//1024} KB)")
