#!/usr/bin/env python3
"""
Offer urgency enrichment (Edge-specific).
Pulls each negotiation counterparty's registered WEEKS from the EdgeOS directory
and turns them into a departure date + days-left + here-now flag — the urgency
engine for the offers view. Writes offers-enrich.js (window.OFFER_DEPARTURES).

Needs: EDGEOS_BEARER_TOKEN (directory read). Personal data -> keep local (gitignored).
Run after build_negotiations.py.
"""
import os, json, re, urllib.request, urllib.parse, datetime

TOK = os.environ.get("EDGEOS_BEARER_TOKEN", "")
POPUP = "43746fd0-bce2-472b-93e4-a438177b2dff"
BASE = "https://api.edgeos.world/api/v1"
TODAY = datetime.date(2026, 6, 11)
# Edge Esmeralda week spans (start, end)
WEEKS = {
    1: (datetime.date(2026,5,30), datetime.date(2026,6,7)),
    2: (datetime.date(2026,6,8),  datetime.date(2026,6,14)),
    3: (datetime.date(2026,6,15), datetime.date(2026,6,21)),
    4: (datetime.date(2026,6,22), datetime.date(2026,6,27)),
}

def api(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + TOK})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

# 1) offer names from the built data
rows = json.loads(open("negotiations-data.js").read().strip()[len("window.RAW_NEGOTIATIONS = "):-1])
# (we enrich everyone present; the display decides who's an offer)

# 2) pull full directory
members, skip = [], 0
while True:
    d = api(f"/applications/my/directory/{POPUP}?skip={skip}&limit=50")
    res = d.get("results", [])
    members += res
    if len(res) < 50:
        break
    skip += 50
print("directory members:", len(members))

def weeks_of(p):
    out = set()
    for x in (p or []):
        m = re.search(r"week\s*(\d)", (x.get("name") or "").lower())
        if m:
            out.add(int(m.group(1)))
    return sorted(out)

dep = {}
for m in members:
    wk = weeks_of(m.get("participation"))
    if not wk:
        continue
    start = WEEKS[wk[0]][0]
    end = WEEKS[wk[-1]][1]
    days_left = (end - TODAY).days
    here_now = start <= TODAY <= end
    arrives_in = (start - TODAY).days if TODAY < start else 0
    full = ((m.get("first_name") or "").strip() + " " + (m.get("last_name") or "").strip()).strip()
    rec = {"weeks": wk, "leaveDate": end.isoformat(), "daysLeft": days_left,
           "hereNow": here_now, "arrivesIn": arrives_in}
    if full:
        dep[full.lower()] = rec
    # first-name fallback key (don't overwrite a full match)
    fn = (m.get("first_name") or "").strip().lower()
    if fn and fn not in dep:
        dep[fn] = rec

# 3) write enrichment keyed by lowercased name (display matches offer names)
with open("offers-enrich.js", "w") as f:
    f.write("window.OFFER_DEPARTURES = " + json.dumps(dep, default=str) + ";\n")
matched = sum(1 for n in rows if False)  # informational only
print(f"departures for {len(dep)} name-keys -> offers-enrich.js ({os.path.getsize('offers-enrich.js')//1024} KB)")
# quick sample of who's leaving soonest among those here now
soon = sorted([(v['daysLeft'], k) for k, v in dep.items() if v['hereNow']])[:8]
print("leaving soonest (here now):", [(k, d) for d, k in soon])
