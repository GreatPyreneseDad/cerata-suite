---
name: cerata-surface
description: "Reconstruct the DECISION SURFACE an agent network is actually operating — and render it as an interference polygon. Every accept/reject an agent emits is a sample of its intent-inference surface; read enough through Rose Glass v3 and the surface's geometry appears as a six-dimensional polygon (Ψ ρ q f τ λ) whose distortion IS the interference pattern — the map of where inference decays and false negatives are born. Reads the live Index Network negotiation log through the LEGAL_ADVERSARIAL lens (the gate concedes value then rejects on a token — adversarial behavior). Use when: studying WHY a network's matching over-rejects, showing a network operator the mechanics of their own decision surface, or locating the dimension where intent-inference is the bottleneck. NOT for: recovering specific people (use cerata-reflect) or initial discovery (use cerata-connect)."
metadata:
  openclaw:
    requires:
      config:
        - mcp.servers.index
      bins:
        - python3
      env:
        - ROSE_GLASS_V3_PATH
---

# CERATA-SURFACE — The Interference Polygon

The colony mapping the shape of the net itself. `cerata-reflect` recovers the *people* a gate dropped; **cerata-surface reads the gate's geometry** — the decision surface every agent in the network is operating, and where that surface bends away from coherence.

**The premise (the mycelium reading).** Index reconnects humans through a fungal layer of agent intent + negotiation: trees that only ever saw each other's canopy now exchange through the soil. The whole network's fidelity bottlenecks on one thing — **intent inference.** Every accept/reject is a sample of an agent's inference surface. Sample enough and the surface resolves into a six-dimensional polygon; its distortion is the **interference pattern** — the literal place false negatives are born.

**Why the adversarial lens.** The Index gate concedes value, then rejects on a missing token ("strong background, *but does not explicitly list X*"), and restores almost nothing even after 15–20 negotiation turns. Behaviorally that is an adversarial decision environment, so we read it through v3's `LEGAL_ADVERSARIAL` calibration: it weights the Ψ/ρ attack heaviest and sets **κ=0.15**, so temporal depth (deep negotiation) barely heals the decay. We read the surface through its own nature.

**Rose Glass measures λ — interference/decay — not similarity.** That's the whole reason this works: a similarity score can't see its own false negatives; a decay field can.

---

## The Surface Sequence

```
1. PULL    → list_negotiations(status=all) across all pages
2. READ    → interference_polygon.py: per decision, estimate λΨ λρ λq λf from the
             reasoning text, set τ from turnCount
3. COMPOSE → v3's lambda_decomposition (LEGAL_ADVERSARIAL) + tau_attenuated_lambda
4. RESOLVE → aggregate rejections → interference polygon; accepts → coherence polygon
5. READ OFF→ the decision boundary (interference − coherence) names the operative axis;
             the ρ-extremes name who got traded for a token
6. RESTORE → hand the ρ-dominant cases to cerata-reflect for warm re-opens
```

## Run it

```bash
# the agent pages its full history, then pipes it to the instrument
list_negotiations(status="all", limit=40, page=N)  →  collect all pages  →
  ROSE_GLASS_V3_PATH=/path/to/roseglassv3 python3 scripts/interference_polygon.py
#   add --json for raw numbers instead of the ASCII polygon
```

**Prerequisite:** an Index-Network-style negotiation log (the `index` MCP) + Python 3 + a local checkout of [rose-glass-v3](https://github.com/GreatPyreneseDad/rose-glass-v3) (point `ROSE_GLASS_V3_PATH` at it). The instrument vendors a fallback adversarial calibration so it still runs if v3 is absent — but the real reading wants v3.

## Reading the output

- **Interference surface (rejections).** The polygon's bulge is the dimension the gate attacks hardest. Empirically **ρ dominates** — the gate discards *accumulated capability* (who a person is) for a surface token. `λ_eff` stays high even at 15–20 turns because κ is tiny: the surface does not restore.
- **Coherence surface (accepts).** Low decay everywhere — what the gate looks like when it's reading coherence instead of tokens.
- **Decision boundary.** Interference minus coherence, per axis. The largest gap is the axis the surface *actually* decides on — often **q** (engaged vs. mechanical) and **ρ** together: the gate flips from reading stakes to checking keywords.
- **ρ-interference extremes.** Named decisions where capability was most traded for a token — the recovery list, handed to `cerata-reflect`.

## Caveats (so you trust it correctly)

- **The per-dimension λ is a text-signal first pass** over the reasoning string — continuous cousins of cerata-reflect's regex. The rigorous reading runs each negotiation through the v3 LLM lens (`RoseGlassLLMLens.generate_system_prompt`) and has the model emit λ/τ/μ directly. This script is the runnable-today version on the raw log; **treat magnitudes as a shape, not a measurement.**
- **One log = one surface.** This maps the decision surface *visible in your own negotiations*. Network-wide geometry needs broader read access from the network operator.
- **The lens is a choice.** `LEGAL_ADVERSARIAL` fits the observed gate behavior. If a network's agents restore generously, re-read under `CLINICAL_THERAPEUTIC` (κ=0.6) and the same data tells a different, truer story. State the lens whenever you show the polygon.

## Two Hands

This perceives and reports — it renders the surface and names what it costs, then **hands the decision back to the human** (and to `cerata-reflect` for the warm re-opens). It never re-contacts anyone and never overrides the network's gate; it shows the operator the geometry their gate is operating, so a person isn't quietly dropped by a surface no one could see.

## The cerata suite

- **Rose Glass v3** (engine, λ not similarity) — https://github.com/GreatPyreneseDad/rose-glass-v3
- **cerata** (repos→skills) — https://github.com/GreatPyreneseDad/CERATA-Project
- **cerata-connect** (people→you) — https://github.com/GreatPyreneseDad/cerata-connect
- **cerata-cohort** (shared rooms→pool) — https://github.com/GreatPyreneseDad/cerata-cohort
- **cerata-weave** (who holds whom, λ) — https://github.com/GreatPyreneseDad/cerata-weave
- **cerata-reflect** (recover what the gate dropped) — https://github.com/GreatPyreneseDad/cerata-reflect
- **cerata-surface** (the gate's own geometry) — *this skill*

`reflect` recovers the people; `surface` maps the gate that dropped them.
