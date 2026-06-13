-- cerata derived layer — the analytics formerly in panel/build_forecast.py,
-- expressed as SQL over the normalized facts. Louvain clustering stays in the
-- ingest (graph algorithm); everything downstream of the cluster assignment —
-- signatures, co-attendance, enjoyment proxy, affinity, predictions, market
-- bids — derives live from cerata.attendance.

-- Attendee count per event (distinct by PK construction).
create view cerata.v_event_stats as
select e.id as event_id, count(a.person_id)::int as attendee_count
from cerata.events e
left join cerata.attendance a on a.event_id = e.id
group by e.id;

-- Current-run cohort assignment per person.
create view cerata.v_person_cohort as
select cm.person_id, c.idx as cohort_idx, c.label as cohort_label
from cerata.cohort_members cm
join cerata.cohorts c on c.id = cm.cohort_id
join cerata.cohort_runs r on r.id = c.run_id and r.is_current;

-- Niche events: 3–25 attendees. Communal mega-events carry no cohort signal.
create view cerata.v_niche_events as
select event_id, attendee_count
from cerata.v_event_stats
where attendee_count between 3 and 25;

-- Co-attendance pairs over niche events: count and log-damped weight
-- (w = 1/ln(2 + room size); a shared small room says more than a shared crowd).
create view cerata.v_co_attendance as
select a1.person_id as person_a,
       a2.person_id as person_b,
       count(*)::int as shared_n,
       sum(1.0 / ln(2 + n.attendee_count))::numeric as shared_w
from cerata.attendance a1
join cerata.attendance a2
  on a2.event_id = a1.event_id and a2.person_id > a1.person_id
join cerata.v_niche_events n on n.event_id = a1.event_id
group by a1.person_id, a2.person_id;

-- Enjoyment proxy per event: of its attendees, the fraction who came back to
-- the same host / same track elsewhere. Reattendance is the etiquette-proof
-- signal; NULL = event has no host/track to return to, not "zero enjoyment".
create view cerata.v_enjoyment as
select e.id as event_id,
  case when e.host is null or e.host = '' then null else
    round(avg((exists (
      select 1 from cerata.attendance a2
      join cerata.events e2 on e2.id = a2.event_id
      where a2.person_id = a.person_id and a2.event_id <> e.id and e2.host = e.host
    ))::int::numeric), 3) end as host_return,
  case when e.track is null then null else
    round(avg((exists (
      select 1 from cerata.attendance a2
      join cerata.events e2 on e2.id = a2.event_id
      where a2.person_id = a.person_id and a2.event_id <> e.id and e2.track = e.track
    ))::int::numeric), 3) end as track_return
from cerata.events e
join cerata.attendance a on a.event_id = e.id
group by e.id, e.host, e.track;

-- Attendance rows tagged with the attendee's current cohort.
create view cerata.v_cohort_attendance as
select pc.cohort_idx, a.person_id, a.event_id
from cerata.attendance a
join cerata.v_person_cohort pc on pc.person_id = a.person_id;

-- Cohort affinity: propensity over track / host / tag from past attendance.
-- All three families normalize by the cohort's total attendance rows,
-- matching the original builder exactly.
create view cerata.v_cohort_affinity as
with tot as (
  select cohort_idx, count(*)::numeric as tot
  from cerata.v_cohort_attendance group by cohort_idx
), tr as (
  select ca.cohort_idx, jsonb_object_agg(k, n) as j from (
    select ca.cohort_idx, e.track as k, count(*)::numeric as n
    from cerata.v_cohort_attendance ca
    join cerata.events e on e.id = ca.event_id
    where e.track is not null
    group by ca.cohort_idx, e.track
  ) ca group by ca.cohort_idx
), ho as (
  select ca.cohort_idx, jsonb_object_agg(k, n) as j from (
    select ca.cohort_idx, e.host as k, count(*)::numeric as n
    from cerata.v_cohort_attendance ca
    join cerata.events e on e.id = ca.event_id
    where e.host is not null and e.host <> ''
    group by ca.cohort_idx, e.host
  ) ca group by ca.cohort_idx
), tg as (
  select ca.cohort_idx, jsonb_object_agg(k, n) as j from (
    select ca.cohort_idx, t.tag as k, count(*)::numeric as n
    from cerata.v_cohort_attendance ca
    join cerata.events e on e.id = ca.event_id
    cross join lateral unnest(e.tags) as t(tag)
    group by ca.cohort_idx, t.tag
  ) ca group by ca.cohort_idx
)
select tot.cohort_idx, tot.tot,
       coalesce(tr.j, '{}'::jsonb) as track_n,
       coalesce(ho.j, '{}'::jsonb) as host_n,
       coalesce(tg.j, '{}'::jsonb) as tag_n
from tot
left join tr on tr.cohort_idx = tot.cohort_idx
left join ho on ho.cohort_idx = tot.cohort_idx
left join tg on tg.cohort_idx = tot.cohort_idx;

-- How many members of each cohort attend each event (prediction substrate).
create view cerata.v_cohort_class as
select cohort_idx, event_id, count(*)::int as members
from cerata.v_cohort_attendance
group by cohort_idx, event_id;

-- Per-person class count.
create view cerata.v_person_stats as
select p.id as person_id, p.alias, count(a.event_id)::int as n_classes,
       pc.cohort_idx, pc.cohort_label
from cerata.people p
left join cerata.attendance a on a.person_id = p.id
left join cerata.v_person_cohort pc on pc.person_id = p.id
group by p.id, p.alias, pc.cohort_idx, pc.cohort_label;

-- Bid of an upcoming event for a person, priced from their cohort's revealed
-- affinity: 0.45·track + 0.30·host + 0.25·mean(tag).
create function cerata.bid(p_cohort_idx int, p_event cerata.events)
returns numeric
language sql stable
as $$
  select 0.45 * coalesce((aff.track_n ->> p_event.track)::numeric / aff.tot, 0)
       + 0.30 * coalesce((aff.host_n  ->> p_event.host )::numeric / aff.tot, 0)
       + 0.25 * coalesce((
           select avg(coalesce((aff.tag_n ->> t.tag)::numeric / aff.tot, 0))
           from unnest(p_event.tags) as t(tag)
         ), 0)
  from cerata.v_cohort_affinity aff
  where aff.cohort_idx = p_cohort_idx
$$;
comment on function cerata.bid(int, cerata.events) is
  'Predicted-enjoyment bid an event places for one person''s attention. Relative, unitless; the market normalizes per person.';
