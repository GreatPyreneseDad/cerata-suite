# cerata on Supabase

The laptop pipeline (`panel/build_forecast.py` → gitignored `forecast-data.js` → double-click HTML)
re-platformed as a server: normalized facts in Postgres, analytics in SQL, reads served by RPC,
frontend in [`web/`](../web).

```
EdgeOS pull ──ingest──▶  cerata schema (private, RLS deny-all)
                          people · events · attendance · cohort_runs/cohorts/members
                                │
                          SQL views (live derivations)
                          co-attendance · enjoyment proxy · cohort affinity · predictions
                                │
                          public RPCs (security definer, pseudonymous JSON)
                          cerata_bootstrap · cerata_person · cerata_class · cerata_market
                                │
                          web/ (Vite + React, publishable key only)
```

## Schema semantics (the roseglassdata.com discipline)

Every column carries a comment stating its **collection method**, its **NULL semantics**, and any
**proxy risk** — read them with `\d+` or in the Studio. The load-bearing ones:

- `attendance.checked_in_at` — NULL means *no check-in record* (~0.3% scanner coverage), never "did not attend".
- `attendance.provenance` — enum `rsvp | checkin | stated | imported`; `stated` is etiquette-inflated and ranked lowest-trust by construction.
- `events.track` — NULL means *no track assigned at source*; flagged as a proxy for cohort membership.
- `people` — only `sha256(local_salt ‖ profile_id)` and a deterministic pseudonym. **Real names never
  reach the database.** The salt lives in `ingest/.salt` (gitignored) on the operator's machine.

## What moved server-side

Everything downstream of Louvain: per-event enjoyment proxy (host/track reattendance), niche
co-attendance pairs, cohort affinity, predicted-next-classes, and the **attention market clearing**
(`public.cerata_market`) — each future time-slot with ≥2 candidates clears to the top
cohort-affinity bid, with the top-two spread reported as opportunity cost. Louvain itself stays in
the ingest (`ingest/ingest_edge_pull.py`), versioned by `cohort_runs` so reads are reproducible.

## Operating it

```bash
# 1. migrations (already applied to project boupwgkkzexwisctrhdr)
#    supabase/migrations/0001..0003

# 2. ingest from a fresh EdgeOS pull
python3 supabase/ingest/ingest_edge_pull.py \
  --pull /tmp/edge_pull.json \
  --forecast panel/forecast-data.js          # optional: upcoming-events inventory
# emits idempotent SQL chunks; apply with psql, or POST JSON batches to the
# cerata-ingest edge function (set CERATA_INGEST_TOKEN as a function secret first).

# 3. frontend
cd web && npm install && npm run dev
```

Security posture: the `cerata` schema is not exposed through PostgREST and is RLS-locked
deny-all; the browser holds only the publishable key; the four RPCs return pseudonyms and public
calendar data only; the ingest function refuses requests unless `CERATA_INGEST_TOKEN` is set and
matched.
