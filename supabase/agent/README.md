# rose_glass_live — the live perception agent

Pulls fresh language from the network, reads each voice through the Rose Glass
lens panel, and ships only the perception (per-lens Ψ ρ q f τ, the between-lens
variance λ, the Veritas flag) to the cerata schema. Raw text and real names
never leave the operator's machine.

## What it does each pass

1. **Pull** — `bun read-messages.ts <chat>` via [telegram-cli-scripts]; aggregate
   the most-active voices into per-author text (the workflow in
   `../../skills/cerata-weave/workflows/telegram-weave.md`).
2. **Resolve identity** — match each author to the EdgeOS attendance pull by name,
   hash with the same local salt as the attendance ingest. A Telegram voice lands
   on the same pseudonymous person row as that person's RSVPs; unmatched voices get
   a `tg:`-namespaced hash + their own pseudonym.
3. **Perceive** — read each voice through the lens panel:
   - `--perceiver bridge`: POST to a running rose-glass-horizon bridge (Gemini + Claude).
   - `--perceiver pending`: emit `/tmp/cerata_pending_signals.json` for an agent
     session to perceive with the four-lens `rose_glass_perceive` MCP, then
     `--ship-reads`.
4. **Ship** — POST `{kind:"perceptions"}` to the `cerata-ingest` edge function.

## Env

| var | meaning |
|---|---|
| `CERATA_ANON_KEY` | Supabase publishable/anon key (function auth) |
| `CERATA_INGEST_TOKEN` | the `cerata-ingest` function secret |
| `CERATA_SUPABASE_URL` | project URL (defaults to rose-glass-data) |
| `CERATA_EDGE_PULL` | path to the EdgeOS pull for identity matching (default `/tmp/edge_pull.json`) |
| `TELEGRAM_CLI_DIR` | telegram-cli-scripts checkout (default `~/telegram-cli-scripts`) |

## Privacy contract

The agent is the only place raw conversation is ever touched, and it touches it
in memory only. What persists server-side is: a salted irreversible person hash,
a content hash, a character count, a time window, and the dimensional readings.
The reading is kept; the conversation is not.

[telegram-cli-scripts]: https://github.com/timkosters/telegram-cli-scripts
