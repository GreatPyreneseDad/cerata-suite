# 🪸 Negotiations panel

**A drop-in web display for your agent's Index negotiation history — anyone loads their own data.**

323 negotiations is unreadable in a chat. This panel renders them: it runs [cerata-reflect](../skills/cerata-reflect)'s classification and [cerata-surface](../skills/cerata-surface)'s decision-surface read **client-side in your browser**, so you can see — at a glance — who accepted, who reached out to *you*, and the **connections your gate wrongly rejected** (the re-open candidates).

Self-contained: one HTML file, opens by double-click, **nothing leaves the page.**

## Load your data — two ways

**A. Paste / upload (zero setup).** Open `index.html`; it shows a loader. Paste your Index `list_negotiations` output (all pages — an array, or `{data:{negotiations:[…]}}`) or drop a `.json` file. It classifies and renders instantly.

**B. Pre-build (agent path).** Have your agent page its full history, then:
```bash
python3 build_negotiations.py page1.json page2.json …   # -> negotiations-data.js
# or:  cat *.json | python3 build_negotiations.py
open index.html                                          # auto-loads window.RAW_NEGOTIATIONS
```

The expected input is the standard `list_negotiations` shape — each record needs at least
`counterpartyId`, `latestAction` (`accept`/`reject`), `latestMessagePreview` (the reasoning), `role`, `turnCount`.

## What it shows

- **Decision surface** — where rejections concentrate across the four axes (f role/keyword · ρ capability · Ψ contradiction · q mechanical). The dominant axis is your gate's *lever* — usually **f** (keyword literalism); **ρ** is the *cost* (capability discarded).
- **Re-open candidates** — rejections that conceded value but rejected on scope: likely **false negatives**. Warm re-opens re-score ~95. Highlighted up top.
- **Filterable table** — Accepted · Inbound (came to you) · Re-open · True mismatches · Glitched. Search by name or reasoning; click a row to read the agent's full rationale.

## Privacy

The generated `negotiations-data.js` contains other people's **names and the reasoning about them** — it's **gitignored and must stay local.** The repo ships the display + builder, never the data. The paste/upload path never persists anything.

## Two Hands

It perceives and reports — surfaces what the gate did and what it cost, then hands the decision to you. Re-open candidates are *surfaced*, never auto-contacted. Your hand closes every connection.

---
Part of the **[cerata suite](../README.md)** · pairs with [cerata-reflect](../skills/cerata-reflect) (the classifier) and [cerata-surface](../skills/cerata-surface) (the polygon).
