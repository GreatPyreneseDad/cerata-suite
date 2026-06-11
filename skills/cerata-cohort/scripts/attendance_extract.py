#!/usr/bin/env python3
"""
EdgeOS attendance extraction + cohort inference (cerata-cohort predictor, live data).
Pulls all events -> per-event rosters -> people x classes matrix -> co-attendance
clusters. Measures check-in coverage (the reliability ceiling). Stdlib only.
"""
import os, json, urllib.request, urllib.parse, urllib.error, time, math
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, Counter

KEY = os.environ.get("EDGEOS_API_KEY", "")  # export EDGEOS_API_KEY=eos_live_...
POPUP = "43746fd0-bce2-472b-93e4-a438177b2dff"
BASE = "https://api.edgeos.world/api/v1"
WIN = {"start_after": "2026-05-30T07:00:00Z", "start_before": "2026-06-28T07:00:00Z"}

def api(path, params, retries=4):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    for a in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Authorization": "Bearer " + KEY})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(float(e.headers.get("Retry-After", "2"))); continue
            if 500 <= e.code < 600:
                time.sleep(1.5 * (a + 1)); continue
            return None
        except Exception:
            time.sleep(1.0 * (a + 1))
    return None

# 1) all published events in the popup window (paginate)
events, skip = [], 0
while True:
    d = api("/events/portal/events", {"popup_id": POPUP, "event_status": "published",
            "limit": 100, "skip": skip, **WIN})
    res = (d or {}).get("results", [])
    events += res
    if len(res) < 100:
        break
    skip += 100

uniq = {}
for e in events:
    uniq.setdefault(e["id"], e)   # dedupe occurrences -> base event
print(f"events: {len(events)} rows -> {len(uniq)} unique classes")

# 2) per-class rosters, in parallel
def roster(eid):
    rows, skip = [], 0
    while True:
        d = api("/event-participants/portal/participants", {"event_id": eid, "limit": 100, "skip": skip})
        res = (d or {}).get("results", [])
        rows += res
        if len(res) < 100:
            break
        skip += 100
    return eid, rows

rosters = {}
with ThreadPoolExecutor(max_workers=10) as ex:
    for eid, rows in ex.map(roster, list(uniq.keys())):
        rosters[eid] = rows
total_rows = sum(len(r) for r in rosters.values())
print(f"roster rows pulled: {total_rows}")

# 3) build matrix + measure check-in coverage
# person -> set(event_id); person name; per (person,event) occurrence count + checkin
attend = defaultdict(set)          # profile_id -> {event_id}
occ = defaultdict(int)             # (profile_id,event_id) -> # occurrences registered
checkins = 0
name = {}
classes_with_roster = 0
for eid, rows in rosters.items():
    if rows:
        classes_with_roster += 1
    for r in rows:
        pid = r.get("profile_id")
        if not pid:
            continue
        if r.get("status") not in (None, "registered", "checked_in", "attended"):
            continue
        attend[pid].add(eid)
        occ[(pid, eid)] += 1
        if r.get("check_time"):
            checkins += 1
        nm = ((r.get("first_name") or "").strip() + " " + (r.get("last_name") or "").strip()).strip()
        if nm:
            name[pid] = nm

ppl = len(attend)
checkin_cov = checkins / total_rows if total_rows else 0
multi = [p for p, s in attend.items() if len(s) >= 2]
print(f"unique people: {ppl} | classes with >=1 attendee: {classes_with_roster}")
print(f"avg classes/person: {sum(len(s) for s in attend.values())/ppl:.2f} | people with >=2 classes (clusterable): {len(multi)} ({len(multi)/ppl*100:.0f}%)")
print(f"CHECK-IN COVERAGE: {checkin_cov*100:.1f}%  (rows with check_time / all roster rows)  <- reliability ceiling")
sizes = sorted((len(r) for r in rosters.values()), reverse=True)
print(f"attendees/class: median {sizes[len(sizes)//2] if sizes else 0}, max {sizes[0] if sizes else 0}")

# 4) class rarity weight (TF-IDF-ish): rare co-attendance counts more (choice-cost proxy)
csize = {eid: max(1, len(set(r.get('profile_id') for r in rows))) for eid, rows in rosters.items()}
def w(eid):
    return 1.0 / math.log(2 + csize[eid])

# 5) weighted co-attendance graph among multi-attenders, then label propagation
idx = {p: i for i, p in enumerate(multi)}
mset = {p: attend[p] for p in multi}
# invert: event -> people (only multi)
ev_people = defaultdict(list)
for p in multi:
    for eid in mset[p]:
        ev_people[eid].append(p)
adj = defaultdict(lambda: defaultdict(float))
for eid, plist in ev_people.items():
    if len(plist) < 2 or len(plist) > 80:   # skip singletons and mega-logistics events
        continue
    ww = w(eid)
    for i in range(len(plist)):
        for j in range(i + 1, len(plist)):
            a, b = plist[i], plist[j]
            adj[a][b] += ww
            adj[b][a] += ww

# label propagation (deterministic)
label = {p: p for p in multi}
order = sorted(multi, key=lambda p: -len(mset[p]))
for _ in range(20):
    changed = 0
    for p in order:
        if not adj[p]:
            continue
        votes = defaultdict(float)
        for q, wt in adj[p].items():
            votes[label[q]] += wt
        best = max(sorted(votes.items()), key=lambda kv: kv[1])[0]
        if best != label[p]:
            label[p] = best; changed += 1
    if changed == 0:
        break

comm = defaultdict(list)
for p in multi:
    comm[label[p]].append(p)
cohorts = sorted([c for c in comm.values() if len(c) >= 3], key=len, reverse=True)
print(f"\nCOHORTS (>=3 people): {len(cohorts)}  covering {sum(len(c) for c in cohorts)} people")

# 6) explain each top cohort: dominant tracks / tags / hosts + sample members
def meta(eid):
    e = uniq.get(eid, {})
    return e.get("track_title"), e.get("tags") or [], (e.get("host_display_name") or e.get("host_id")), e.get("title")

out = []
for c in cohorts[:8]:
    tracks, tags, hosts, titles = Counter(), Counter(), Counter(), Counter()
    for p in c:
        for eid in mset[p]:
            t, tg, h, ti = meta(eid)
            if t: tracks[t] += 1
            for x in tg: tags[x] += 1
            if h: hosts[h] += 1
            if ti: titles[ti] += 1
    members = sorted(c, key=lambda p: -len(mset[p]))
    rec = {
        "size": len(c),
        "top_tracks": tracks.most_common(3),
        "top_tags": tags.most_common(4),
        "top_hosts": hosts.most_common(3),
        "signature_classes": titles.most_common(4),
        "members": [name.get(p, p[:8]) for p in members[:6]],
    }
    out.append(rec)
    print(f"\n— cohort of {rec['size']} —")
    print(f"  tracks:  {rec['top_tracks']}")
    print(f"  tags:    {rec['top_tags']}")
    print(f"  hosts:   {rec['top_hosts']}")
    print(f"  classes: {rec['signature_classes']}")
    print(f"  members: {', '.join(rec['members'])}")

json.dump({"summary": {"events": len(uniq), "people": ppl, "checkin_coverage": checkin_cov,
           "clusterable": len(multi), "cohorts": len(cohorts)}, "cohorts": out},
          open("/tmp/cohorts.json", "w"), indent=2, default=str)
print("\nsaved -> /tmp/cohorts.json")
