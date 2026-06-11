#!/usr/bin/env python3
"""v3: Louvain modularity on the niche co-attendance graph -> real multi-cohort partition."""
import json, math, os
from collections import defaultdict, Counter

blob = json.load(open("/tmp/edge_pull.json"))
uniq, rosters = blob["uniq"], blob["rosters"]

attend = defaultdict(set); name = {}
for eid, rows in rosters.items():
    for r in rows:
        pid = r.get("profile_id")
        if not pid: continue
        attend[pid].add(eid)
        nm = ((r.get("first_name") or "").strip()+" "+(r.get("last_name") or "").strip()).strip()
        if nm: name[pid] = nm
csize = {eid: len(set(r.get('profile_id') for r in rows if r.get('profile_id'))) for eid, rows in rosters.items()}

LO, HI = 3, 25
niche = {eid for eid, n in csize.items() if LO <= n <= HI}
mset = {p: (attend[p] & niche) for p in attend}
mset = {p: s for p, s in mset.items() if len(s) >= 2}
ev_people = defaultdict(list)
for p, s in mset.items():
    for eid in s: ev_people[eid].append(p)
def w(eid): return 1.0/math.log(2+csize[eid])
shared = defaultdict(float); shared_n = defaultdict(int)
for eid, plist in ev_people.items():
    ww = w(eid)
    for i in range(len(plist)):
        for j in range(i+1, len(plist)):
            k = (plist[i], plist[j]) if plist[i] < plist[j] else (plist[j], plist[i])
            shared[k] += ww; shared_n[k] += 1
adj = defaultdict(dict)
for (a, b), n in shared_n.items():
    if n >= 2:
        adj[a][b] = shared[(a, b)]; adj[b][a] = shared[(a, b)]
nodes = [p for p in mset if p in adj and adj[p]]
print(f"niche [{LO},{HI}]: {len(niche)} classes | nodes: {len(nodes)}")

# ---- Louvain one level (weighted) ----
k = {u: sum(adj[u].values()) for u in nodes}
m = sum(k.values()) / 2.0
comm = {u: u for u in nodes}
Sigma_tot = {u: k[u] for u in nodes}

def neigh_comm(u):
    wc = defaultdict(float)
    for v, wt in adj[u].items():
        wc[comm[v]] += wt
    return wc

improved = True; passes = 0
while improved and passes < 40:
    improved = False; passes += 1
    for u in sorted(nodes, key=lambda x: -k[x]):
        cu = comm[u]
        wc = neigh_comm(u)
        # remove u from its community
        Sigma_tot[cu] -= k[u]
        ku_in_cu = wc.get(cu, 0.0)
        best, bestgain = cu, 0.0
        for c, kiin in wc.items():
            gain = kiin - Sigma_tot[c] * k[u] / (2.0 * m)
            if gain > bestgain:
                bestgain, best = gain, c
        # baseline staying gain
        stay = ku_in_cu - Sigma_tot[cu] * k[u] / (2.0 * m)
        if bestgain <= stay:
            best = cu;
        comm[u] = best; Sigma_tot[best] += k[u]
        if best != cu: improved = True

groups = defaultdict(list)
for u in nodes: groups[comm[u]].append(u)
cohorts = sorted([g for g in groups.values() if len(g) >= 4], key=len, reverse=True)
# modularity
Q = 0.0
for u in nodes:
    for v, wt in adj[u].items():
        if comm[u] == comm[v]:
            Q += wt - k[u]*k[v]/(2*m)
Q /= (2*m)
print(f"cohorts (>=4): {len(cohorts)} covering {sum(len(c) for c in cohorts)} people | modularity Q={Q:.3f}\n")

def meta(eid):
    e = uniq.get(eid, {}); return e.get("track_title"), e.get("tags") or [], (e.get("host_display_name") or e.get("host_id")), e.get("title")
rep = []
for c in cohorts[:14]:
    tracks, tags, hosts, titles = Counter(), Counter(), Counter(), Counter()
    for p in c:
        for eid in mset[p]:
            t, tg, h, ti = meta(eid)
            if t: tracks[t]+=1
            for x in tg: tags[x]+=1
            if h: hosts[h]+=1
            if ti: titles[ti]+=1
    members = sorted(c, key=lambda p:-len(mset[p]))
    r = {"size": len(c), "tags": tags.most_common(3), "tracks": tracks.most_common(2),
         "hosts": hosts.most_common(2), "classes": [t for t,_ in titles.most_common(4)],
         "members":[name.get(p,p[:8]) for p in members[:6]]}
    rep.append(r)
    print(f"— cohort of {r['size']} —")
    print(f"   tags:   {r['tags']}")
    print(f"   track:  {r['tracks']}")
    print(f"   hosts:  {r['hosts']}")
    print(f"   classes:{r['classes']}")
    print(f"   people: {', '.join(r['members'])}\n")
json.dump(rep, open("/tmp/cohorts_v3.json","w"), indent=2, default=str)
print("saved -> /tmp/cohorts_v3.json")
