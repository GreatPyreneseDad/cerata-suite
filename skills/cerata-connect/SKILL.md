---
name: cerata-connect
description: "Hunt and metabolize PEOPLE as connections — fire standing connection vectors through the Index Network, score each candidate's fit through the Rose Glass lens, gate on agent-accept, and register the catch. Use when: the user wants to find/meet/recruit collaborators, surface relevant people at an event or community, fill a project role, or grow their relationship graph. The connection-hunting sibling of `cerata` (which hunts repos for skills) — this one hunts the village for relationships. NOT for: hunting GitHub repos / building skills (use `cerata`), general coding, or one-off lookups of a person already known by name."
homepage: https://github.com/GreatPyreneseDad/CERATA-Project
metadata:
  {
    "openclaw":
      {
        "emoji": "🪸",
        "requires": { "bins": ["curl"] },
      },
  }
---

# CERATA-CONNECT — Connection Hunt Skill Reference

Same predator architecture as `cerata`, pointed at a different prey. Where `cerata` eats GitHub repos and crystallizes **skills** (nematocysts), `cerata-connect` hunts the village and crystallizes **connections**. The colony grows in relationships: every accepted opportunity is a stinging cell that every future hunt can build on.

**Mental model**: the coral reaches into the current and stings what drifts past that fits. Prey = a person's profile + signals. The sting = an accepted opportunity. A connection that never opens is dead weight — write the vector to sting precisely.

**Tool surface**: the `agentvillage:index-network` skill (Index MCP, server `index`) is the hunt engine; `agentvillage:edgeos` is the registration-side fallback for finding a specific person by name/org. The Index **scorer** already runs Rose-Glass-style fit judgment — it *is* `evaluate_prey` for people. Read those skills' tool docs before calling.

---

## The Hunt Sequence

```
1. IDENTIFY → What kind of person/need? (a project role, a peer, a venue, a connector)
2. HUNT     → Fire the vector: discover_opportunities (open searchQuery, or targetUserId)
3. EVALUATE → The scorer rates fit through the Rose Glass lens + writes the reasoning;
              the two agents negotiate (the "is this worth their time" verdict)
4. GATE     → Keep on negotiation ACCEPTED (scorer ≥ 50 + accept). Timed-out / rejected = pass.
5. REGISTER → Log the catch; the opportunity's acceptUrl is the actionable sting
6. FOLLOW-UP→ User opens the connection (acceptUrl) and reaches out — the agent cannot DM
```

Steps 2–4 are one `discover_opportunities` call followed by polling `get_discovery_run` (async). The scorer + negotiation collapse "search, score, and decide" into a single returned verdict per candidate.

---

## Standing Connection Vectors

The analog of `cerata`'s `HUNT_QUERIES` — the colony's standing appetites. Retarget by editing this list or by posting a vector as a signal (`create_intent`) so it hunts passively, around the clock, even while the machine sleeps.

| Vector | Looking for | Rose Glass axis |
|---|---|---|
| `interpretability-peers` | Researchers/builders on AI interpretability and the model–user gap | Ψ consistency |
| `roseglass-deploy` | Design partners / early licensees (voice-AI, enterprise, dating, field services) | infrastructure |
| `working-paper-thinkers` | Coherence math, active inference, biological constraints on cognition | ρ wisdom |
| `hub-greeter-crew` | Robotics/hardware, conversational/voice AI, interaction design | f social |
| `coherence-table` | Attendees for the AI-coherence dinner discussion | τ temporal |
| `connectors` | High-agency people who *know* relevant others (e.g. a "Brennan") | f social |

A vector is concrete enough to hunt when it names **who**, **what for**, and (ideally) a **timeframe**. Vague vectors get bounced by the scorer's specificity gate — narrow before re-firing; never silently re-paraphrase.

---

## How to Hunt

**Open hunt (cast wide).** Fire a vector across the community; the scorer returns whoever fits:
- `discover_opportunities(searchQuery="<vector, in the user's voice>")` → poll `get_discovery_run` → present accepts.
- Paginate with `continueFrom` until the catch goes dry (no new faces, rising rejects = the pool is tapped; stop rather than re-ping).

**Targeted hunt (a known prey).** When a specific person should be stung:
- `discover_opportunities(targetUserId=<id>, searchQuery="<why, in the user's voice>", hint="<reason>")`.
- Find the `userId` first via `read_user_profiles(query=name)` or a roster pull (`read_user_profiles(networkId=...)`).

**Passive hunt (standing appetite).** Post the vector so prey find *you*:
- `create_intent(description="<vector>")` — it indexes and matches around the clock. This is how the hunt runs while you're asleep; the server-side digest surfaces accepts.

**The Rose Glass framing is the bait.** Author each `searchQuery`/`hint` in the user's voice, carrying the spine that makes the connection cohere — *perceive and report before acting*. The scorer's reasoning and the counterpart's negotiation both read it.

---

## The Fit Gate

Keep a catch only when the negotiation outcome is **`accepted`** (mirrors `cerata`'s `confidence ≥ 0.6`):

- `accepted` → register it. The `acceptUrl` is the live sting the user opens.
- `timed_out` → counterpart agent never answered (dormant). Opportunity is a draft — register as *open*, the user can nudge.
- `rejected_or_stalled` → genuine no-fit. Log as a pass with the reasoning; do **not** re-fire the same person on the same vector.

A scorer score (0–100) and the negotiation reasoning come back on every candidate — keep them; they're the catch's provenance.

---

## Two Hands — the hunter's discipline

This hunt touches **real people**, so the predator perceives and reports before it stings:

- **Perceive first.** Pull the roster / profile and assemble a ranked shortlist *before* firing at anyone.
- **Report, then confirm.** Surface the candidates and let the user choose targets before sending opportunities — sending pings a real attendee's agent.
- **Don't blast.** Re-pinging the same crowd, or casting a too-broad vector across everyone, reads as spam — the opposite of a good sting. Hunt where there's genuine overlap.
- **The agent cannot DM.** Index has no outbound message tool; the sting is the `acceptUrl`. To invite/recruit, draft the message and hand it to the user to send in-thread.
- **Honor the voice.** Never "search"/"match"/"network" in user-facing text (see the index MCP's banned vocabulary) — *look for*, *find*, *overlap*, *signal*, *connection*.

---

## Connection Registry

The colony's accumulated relationships — the connection analog of `cerata`'s Nematocyst Registry. Seeded with the hunt of 2026-06-08 (12 targeted + flier + inbound; see Index negotiations for the full set):

| Connection | Vector | Why (overlap) | Status | Date |
|---|---|---|---|---|
| Eric Lacosse | interpretability-peers | cognitive human-AI engineering; model–user gap | accepted | 2026-06-08 |
| Ivan Vendrov | interpretability-peers | alignment, ex-Anthropic/Midjourney | accepted | 2026-06-08 |
| Carson Lorenz-Stewart | interpretability-peers | adversarial manipulation = mirror of honest divergence | accepted | 2026-06-08 |
| Luc Baracat | interpretability-peers | intensional/extensional bridge, legibility | open (agent timed out) | 2026-06-08 |
| Tony Morales | working-paper-thinkers | affective/cognitive neuroscience + governance | accepted | 2026-06-08 |
| Athena Aktipis | working-paper-thinkers | evolutionary cooperation, stealth AI | accepted | 2026-06-08 |
| Robert Raynor | working-paper-thinkers | formalizing coherence (active inference) — inbound | accepted | 2026-06-08 |
| Scott Brylow | hub-greeter-crew | robotics/hardware, Mars-mission cameras | accepted | 2026-06-08 |
| Eileen Jubilee | hub-greeter-crew | AI greeters for a coworking space | accepted | 2026-06-08 |
| Samantha Ouyang | hub-greeter-crew | AI coordination in physical spaces | accepted | 2026-06-08 |
| Paul McKellar | hub-greeter-crew | EE + AI orchestration | accepted | 2026-06-08 |
| Seref Yarar | roseglass-deploy | user modeling/explainability; Index co-founder | accepted | 2026-06-08 |
| Timour Kosters | roseglass-deploy | Edge City co-founder; community + pilot venue | accepted | 2026-06-08 |
| Joe / Othman / Zeshan / Telamon | coherence-table | flagged the class flier worth their time | accepted | 2026-06-08 |
| *(next hunt)* | *(vector)* | *(overlap)* | — | — |

---

## Hunting Priority

When several vectors are live, hunt in this order:

1. **A named, time-bound need** (a role for a project shipping this month) → hunt now.
2. **An inbound proposal** (someone's agent stung *you*) → evaluate and answer before it goes stale.
3. **A connector** (one node who unlocks many) → high leverage, hunt early.
4. **Standing appetite with no urgency** → post as a signal and let it hunt passively.

---

## Notes

- Every hunt should produce a clear catch list — accepts, opens, and passes, each with its reasoning. Silent truncation (a `continueFrom` you didn't run) reads as "covered everyone" when it didn't; say what was left.
- The scorer and intent engine run on a shared model provider; if it's starved (402s), the hunt can't score — report it plainly and retry later, don't fake a catch.
- A connection only counts once it's *opened*. The registry tracks accepts; opening the `acceptUrl` is what puts the person in front of the user.
- Prey not yet in the village (no Index profile) can't be hunted — the move is to get them *in* (share onboarding), after which standing vectors catch them automatically.
