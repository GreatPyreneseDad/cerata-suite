# 🪸 Cerata Panel — step 1 (the reads surface)

A self-contained front-end an **agent can launch for its user**. It loads the cerata plugin
data and lets the user (or the agent) pull up any **class** or **person** and see their *reads* —
cohort, predicted next classes, co-attendees, signature, and an RSVP/reattendance enjoyment proxy.

## Launch

No server, no build — it's one HTML file + one data file.

```
open index.html                      # macOS — opens in the default browser
# or have the agent open it pointed straight at a read:
open "index.html#person=Rungroj Lexx Tancharoen"
open "index.html#class=The Foundation for a Decentralized Cloud - Day 1/5"
open "index.html#cohort=2"
```

The **`#person=` / `#class=` / `#cohort=` hash** is how an agent loads a read for its user:
launch the file with the hash and it lands directly on that read. Inside, the search box does
the same for the user, and every name/cohort/co-attendee is click-through.

## What each read shows

- **Person** → their cohort, *predicted next classes* (what their cohort attends that they haven't,
  ranked by cohort-mates going), strongest co-attendees, signature (tracks/tags/hosts), full class list.
- **Class** → cohort mix (who shows up), the **enjoyment proxy** (did attendees *return* to this
  host / track — the etiquette-proof signal), and the RSVP'd roster.
- **Cohort** → what binds them, signature classes, members.

## Honest caveats (baked into the UI)

- Data is **RSVP**, not confirmed attendance — Edge check-in coverage is **~0.2%**. The panel says so.
- Enjoyment = **cohort reattendance to a host/track**, not confirmed presence.
- Cohorts are Louvain on niche co-attendance (modularity **Q≈0.32**). The AI/tech crowd is a
  diaspora inside a health/wellness-dominated graph, not its own cluster.

## Refresh the data

```
python3 build_forecast.py      # reads /tmp/edge_pull.json -> writes forecast-data.js
```
(`/tmp/edge_pull.json` is the cached EdgeOS events+rosters pull from `attendance_extract.py`.)

## Wiring the rest of the suite

The sidebar lists the other plugins as load slots. To light them up, drop a sibling data file and
add a `<script src>`: `surface-data.js` (cerata-surface decision polygon), `reflect-data.js`
(negotiation reads), `weave-data.js` (λ tables). Same `window.<NAME>` pattern as `forecast-data.js`.
