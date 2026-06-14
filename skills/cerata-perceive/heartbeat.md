# cerata-perceive — Heartbeat Tasks

Per-tick tasks for the Rose Glass node. Walked from the heartbeat tick in
`AGENTS.md`. Track last-run timestamps in `memory/heartbeat-state.json`; skip a
task that isn't due. Quiet by default — anything skipped lands in the next
morning's digest.

---

tasks:

- name: perceive-new-voices
  interval: 6h
  prompt: |
    New language has accumulated since last tick — perceive it and feed the field.

    1. Pull the voices active since the last run (the user's connected groups).
    2. For each voice with enough substance, perceive it through the `rose-glass`
       MCP. Keep every lens read + λ + Veritas; never average to a verdict.
    3. Contribute the reading (hash + dimensions + λ only — never raw text or
       names) to the network. Re-perception is idempotent on the content hash.
    4. Reply silently with this host's no-reply marker — this is background work.

- name: surface-coherence
  interval: 24h
  prompt: |
    Once a day, surface coherence worth the interruption — and only that.

    1. Read the network (`cerata_bootstrap`, and `cerata_person` for the user).
    2. Find a candidate whose reason to surface is specific to THIS user: a strong
       co-attendee they haven't met, a Veritas-clear voice in their cohort, a table
       that would lower both their λ. Generic "interesting profile" does not qualify.
    3. Offer it as Hand 2 — a draft introduction or a note — and hand the decision
       to the user. Draft, never send.
    4. If nothing earns the interruption, skip silently. Silence is correct routing.

- name: legibility-watch
  interval: 7d
  prompt: |
    Once a week, check what the network CAN'T see.

    1. Read `cerata_cultures`. Note the high-blind-spot lenses (low supply, high λ).
    2. If the user belongs to or cares about an underserved culture, tell them
       plainly: the network under-reads this worldview, here's the residual λ.
    3. This is the instrument confessing its own limits — never a label on a person.
