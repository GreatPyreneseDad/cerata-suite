---
name: cerata-cohort
description: "Connect people by shared class attendance. Pull EdgeOS event rosters, compute who keeps ending up in the same rooms (co-attendance = cheap, strong context signal), and surface the cohort — then hand it to cerata-connect (introduce) or cerata-weave (λ-tables within the cohort). Use when: the user wants to meet people from their classes, introduce two attendees who keep overlapping, or seed a higher-signal candidate pool. NOT for: scoring fit (that's connect/weave) or one-off lookups."
metadata:
  openclaw:
    requires:
      config:
        - mcp.servers.index
      bins:
        - curl
        - python3
      env:
        - EDGEOS_API_KEY
---

# CERATA-COHORT — Co-attendance Connector

A shared room is shared context. This skill turns EdgeOS class rosters into a co-attendance graph — who keeps showing up together — and hands that **cohort as a candidate pool** to the rest of the toolchain. It does not score fit; it produces a higher-signal set for `cerata-connect` / `cerata-weave` to work on.

**Engine**: EdgeOS event-participant API (read) + `scripts/cohort.py`. Pairs with `index-network` for the actual introductions.

---

## 1 — Pull the rosters

List the classes (the popup id comes from the active popup skill, e.g. `edge-esmeralda`):

```bash
curl -s -H "Authorization: Bearer $EDGEOS_API_KEY" \
  "https://api.edgeos.world/api/v1/events/portal/events?popup_id={popup_id}&event_status=published&limit=100"
```

Then the attendees of each class:

```bash
curl -s -H "Authorization: Bearer $EDGEOS_API_KEY" \
  "https://api.edgeos.world/api/v1/event-participants/portal/participants?event_id={event_id}&limit=100"
```

Each participant record carries `first_name` / `last_name` (+ `status`). Build a `{ "Class title": ["Name", ...] }` map across the classes you care about (a track, a day, or the user's own attended set).

## 2 — Compute the cohort

```bash
echo '{"events":{"Class A":["..."],"Class B":["..."]}, "target":"<Name>"?, "top":12}' \
  | python3 scripts/cohort.py
```

- **With `target`** → that person's co-attendees, ranked by # shared classes (and which).
- **Without `target`** → the strongest co-attendance *pairs* across everyone — the intros worth making as a connector.

## 3 — Connect (hand off to the toolchain)

Co-attendance is the pool, not the matcher:

- **Introduce** a strong pair: `cerata-connect` / Index Introduction mode (`partyUserIds` or `introTargetUserId`). Match the co-attendee names to Index `userId`s via `read_user_profiles(query=name)`.
- **Weave** a cohort: pass the co-attendees as `cerata-weave`'s candidate pool — find the λ-tables *within* the people who already share rooms (high-signal, since context is established).

---

## Two Hands

- Co-attendance is a *signal*, not consent. **Surface the cohort and let the user pick** before any introduction is sent.
- Don't introduce strangers on a single shared class as if it's a strong tie — rank by count, and say how thin a 1× overlap is.
- The agent can't DM; introductions go through Index opportunities the parties open. Draft the note; the user sends it.
- Names from rosters are the user's own accessible event data — don't expose contact details beyond what's needed to make the intro.
