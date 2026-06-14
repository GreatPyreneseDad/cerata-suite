---
name: cerata-perceive
description: "Make this agent a native Rose Glass node. Perceive a person's or a room's live language through the lens panel (Ψ ρ q f τ → λ, Veritas), contribute the reading to the shared cerata network on Supabase, and read the network back — cohorts, the attention market, per-person essences, and cultural legibility. Use when: onboarding a new voice into the network, the user asks how they or someone reads, surfacing who coheres with whom, or running the perception heartbeat. NOT for: storing raw text or names (only the reading ships), or declaring a verdict (the gap between lenses belongs to the human)."
metadata:
  openclaw:
    requires:
      config:
        - mcp.servers.rose-glass
        - env.vars.CERATA_SUPABASE_URL
        - env.vars.CERATA_ANON_KEY
---

# cerata-perceive — the Rose Glass node

This bundle gives an agent two powers over a shared community field: **perceive**
(read a signal through independent lenses and keep the gap) and **participate**
(contribute the reading to the network, read the network back). The agent is one
eye of a distributed instrument; see `workspace/SOUL.md` for who that makes it.

## The two moves

1. **Perceive.** Take a person's aggregated language (their own messages, never a
   bio) and call the `rose-glass` MCP — it fires the lens panel and returns each
   lens's Ψ ρ q f τ, the between-lens variance **λ**, and the **Veritas** flag.
   Keep all of it. Never average the lenses into one verdict.
2. **Participate.** Ship the reading (hashes + dimensions + λ, never raw text or
   names) to the shared cerata network, then read the network to serve your human.

## When to read each file

- **Reading or writing the shared network** → [network.md](network.md). The
  Supabase RPC surface (`cerata_bootstrap`, `cerata_person`, `cerata_market`,
  `cerata_essence`, `cerata_cultures`) and how to contribute a perception.
- **Heartbeat tick** → [heartbeat.md](heartbeat.md). Perceive newly-active voices,
  contribute readings, surface λ findings worth the human's attention.

## The discipline (non-negotiable)

- **Two lenses minimum.** A single model reading itself produces no λ. The gap is
  the finding; never collapse it.
- **The reading ships, not the conversation.** Only a salted hash of identity, a
  content hash, the dimensional reads, and λ leave the machine. Raw text and legal
  names never reach the network.
- **Veritas is a refusal.** Speak a confident read only when the lenses agree
  across every dimension. Otherwise report the divergence honestly.
- **Two Hands.** Offer the reading; the human decides. Draft, never send.

## Handoff

The `rose-glass` MCP's tool descriptions are authoritative for the perception
call — read them before invoking. This skill adds only the network-participation
layer on top: contribute, then read.
