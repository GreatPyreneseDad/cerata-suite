# cerata on Supabase

The laptop pipeline (`panel/build_forecast.py` → gitignored `forecast-data.js` → double-click HTML)
re-platformed as a server: normalized facts in Postgres, analytics in SQL, reads served by RPC,
frontend in [`web/`](../web).

```
EdgeOS pull ──ingest──▶  cerata schema (private, RLS deny-all)
                          people · events · attendance · cohort_runs/cohorts/members
Telegram / geo ──┐            signals · lens_reads · perceptions
  live agent ────┘                │
                          SQL views (live derivations)
                          co-attendance · enjoyment proxy · cohort affinity · predictions · essence
                                │
                          public RPCs (security definer, pseudonymous JSON)
                          cerata_bootstrap · cerata_person · cerata_class · cerata_market
                          cerata_essence · cerata_essences
                                │
                          web/ (Vite + React, publishable key only)
                          reads · attention market · essence wall (interference polygons + λ)
```

## The live perception layer (Rose Glass)

Beyond counting RSVPs, the platform reads people through the **Rose Glass** lens
panel and stores the *perception*, never the words. The flow:

```
agent/rose_glass_live.py
  pull telegram (telegram-cli-scripts)  →  aggregate per voice
  → match identity to EdgeOS pull (same local salt)  →  pseudonym
  → perceive each voice through the lens panel (Gemini + Claude, or 4-lens MCP)
  → ship {kind:"perceptions"} : per-lens Ψ ρ q f τ, λ=σ² between lenses, Veritas
```

The structural invariant from names extends to words: **raw text never reaches
the database.** A `cerata.signals` row holds only a content hash, length, and
window; `cerata.lens_reads` holds each lens's five-dimension reading; and
`cerata.perceptions` holds λ (the between-lens variance) and the Veritas flag —
true only when every dimension's σ² is under threshold. No synthesis: the
lenses are never averaged into a verdict; **the gap between them is the finding.**

Run it:

```bash
export CERATA_ANON_KEY=...           # publishable/anon key (function auth)
export CERATA_INGEST_TOKEN=...       # the cerata-ingest secret

# two-lens bridge (rose-glass-horizon running on :8000)
python3 supabase/agent/rose_glass_live.py --chat "Edge Esmeralda 2026" --perceiver bridge

# live loop every 20 min
python3 supabase/agent/rose_glass_live.py --watch 1200 --perceiver bridge

# or: agent-driven 4-lens perception via the rose-glass-horizon MCP
python3 supabase/agent/rose_glass_live.py --perceiver pending   # writes /tmp/cerata_pending_signals.json
# (an agent perceives each signal_text with rose_glass_perceive, attaches reads/lambda/veritas)
python3 supabase/agent/rose_glass_live.py --ship-reads /tmp/cerata_perceived.json
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
