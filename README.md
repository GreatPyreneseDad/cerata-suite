# 🪸 cerata

**A suite of agent skills for seeing the people around you — and a panel that displays what they see.**

cerata gives an AI agent *eyes for a community*: who its human should meet, who holds whom, who keeps sharing rooms, who the agent quietly filtered out and shouldn't have — and, now, **what its human will actually enjoy.** Every tool is built on **[Rose Glass](https://github.com/GreatPyreneseDad/rose-glass-v3)**, an open framework that measures **coherence between minds as a real signal — λ, not similarity.**

It's portable: **feed your agent a tool's folder and go.** One repo, all the tools, plus the display.

> Built at Edge Esmeralda 2026. Runs on Hermes / OpenClaw / Claude Code agents.

---

## The loop

cerata is one idea applied end to end — **stop trusting what gets *said* (etiquette inflates it; agents soften it); measure what gets *done*.**

```
PERCEIVE  →  PREDICT  →  PRICE  →  SETTLE
 read people    cohort        attention      revealed
 through the    pattern       market          behavior
 lens (λ)       inference     (allocation)    (reattendance)
```

- **Perceive** — read each person through Rose Glass; find tables that hold each other's coherence.
- **Predict** — cluster revealed co-attendance into cohorts; a person's cohort predicts what they'll attend and enjoy.
- **Price** — attention is finite, so it's tradeable: competing classes *bid* for it with predicted enjoyment; the market clears.
- **Settle** — positions resolve on **revealed behavior** (reattendance), never on surveys or polite chat.

---

## What's inside

| | tool | what it hunts | folder |
|---|---|---|---|
| engine | **Rose Glass v3** | coherence between minds — six dims (Ψ ρ q f τ λ) | [↗ repo](https://github.com/GreatPyreneseDad/rose-glass-v3) |
| 🔍 | **cerata-connect** | the people you should meet | [`skills/cerata-connect`](skills/cerata-connect) |
| 🏛 | **cerata-cohort** | co-attendance → cohorts → **attendance/enjoyment prediction** | [`skills/cerata-cohort`](skills/cerata-cohort) |
| 🕸 | **cerata-weave** | the tables that hold each other's λ | [`skills/cerata-weave`](skills/cerata-weave) |
| ♻️ | **cerata-reflect** | the connections your gate wrongly rejected | [`skills/cerata-reflect`](skills/cerata-reflect) |
| 📐 | **cerata-surface** | the geometry of your agent's own decision surface | [`skills/cerata-surface`](skills/cerata-surface) |
| 🖥 | **the panel** | the display — reads + the attention market | [`panel/`](panel) |
| 📋 | **negotiations panel** | display your agent's negotiation history (reflect + surface, client-side) | [`negotiations-panel/`](negotiations-panel) |

`connect` finds people *for* you · `weave` finds who holds *whom* · `cohort` predicts who goes where · `reflect` recovers who the gate dropped · `surface` shows the gate that dropped them · the **panel** renders the reads + runs the attention market · the **negotiations panel** displays your whole negotiation history (drop in your own `list_negotiations` export — classification runs in your browser).

---

## The panel — the display

A self-contained front-end an agent **launches for its user** (`panel/index.html` — no server, opens by double-click):

- **Reads tab** — load any **class** or **person**, see their read: cohort, predicted next classes, co-attendees, signature, and an RSVP/reattendance **enjoyment proxy**.
- **Attention Market tab** — your finite attention is allocated across competing time-slots; classes *bid* with their predicted enjoyment for you; the market clears to the winner and shows the **opportunity cost** of going elsewhere. Single-player by design — works at N=1, no universal adoption required.
- Agent-launch: open `index.html#person=Name` / `#class=Title` / `#market=Name` and it lands straight on that read.

### Run the pipeline

```bash
export EDGEOS_API_KEY=eos_live_...          # an EdgeOS automation key

# 1. pull attendance + cluster cohorts (Louvain on niche co-attendance)
python3 skills/cerata-cohort/scripts/attendance_extract.py     # -> /tmp/edge_pull.json
python3 skills/cerata-cohort/scripts/cohort_cluster.py         # the 6 cohorts, modularity Q

# 2. build the panel's data (per-class & per-person reads + the live market)
python3 panel/build_forecast.py            # reads /tmp/edge_pull.json -> panel/forecast-data.js

# 3. launch
open panel/index.html
```

---

## Honest by construction (the caveats are the point)

- **We measure revealed behavior, not stated signal.** Politeness inflates surveys and chat; agents soften them further. Reattendance, propagation, and co-attendance can't lie the same way.
- **It's RSVP, not confirmed presence** where check-in coverage is thin (~0.2% at Edge Esmeralda). Enjoyment = cohort reattendance to a host/track, stated plainly in the UI.
- **Cohorts are Louvain on niche co-attendance** (modularity ≈ 0.32 on real data). A dominant communal track can mask finer cohorts — strip the backbone before clustering.
- **The data file is never published.** `panel/forecast-data.js` holds real attendee names/RSVPs and is gitignored. You generate it locally.

## Two Hands

Every tool **perceives and reports, then hands the decision to the human.** It drafts, never sends; it surfaces, never auto-contacts; it shows your agent what its gate cost without overriding the gate. The human's hand closes every connection.

## License

[MIT](./LICENSE) — adopt, fork, retarget freely. Rose Glass v3 is GPL-3.0 (linked, not vendored).

---

## Run it as an AgentVillage plugin (native Rose Glass agents)

cerata installs as an [AgentVillage](https://github.com/Edge-City/agentvillage) /
OpenClaw plugin, turning every village agent into a **Rose Glass node** in a
distributed network. Manifests: `openclaw.plugin.json`, `marketplace.json`,
`mcp.json` (registers the `rose-glass` perceiver + `index`). Agent core:
`workspace/SOUL.md`. Native bundle: [`skills/cerata-perceive`](skills/cerata-perceive)
— perceive a voice through the lens panel, contribute the reading (hashes +
dimensions + λ, never raw text or names) to the shared cerata network on Supabase,
read the network back (cohorts, attention market, essences, cultural legibility).

Each agent serves one human; together they hold one shared reading of the
community. The intelligence lives in the field — `skills/cerata-perceive/network.md`
is the RPC surface, `heartbeat.md` the per-tick perceive→contribute→surface loop.
Alongside the existing `cerata-connect / cohort / weave / reflect / surface`
bundles, this makes the suite a complete native-agent package: discovery and
coherence measured as **λ, not similarity**.
