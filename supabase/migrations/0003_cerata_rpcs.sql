-- cerata public API — four security-definer RPCs. These are the ONLY doors
-- into the cerata schema: they return pseudonymous reads computed live from
-- the normalized facts. PostgREST exposes them at /rest/v1/rpc/cerata_*.

create function public.cerata_bootstrap()
returns jsonb
language sql stable security definer set search_path = ''
as $$
select jsonb_build_object(
  'meta', jsonb_build_object(
    'people',   (select count(*) from cerata.people),
    'classes',  (select count(*) from cerata.events where starts_at <= now()),
    'upcoming', (select count(*) from cerata.events where starts_at > now()),
    'cohorts',  (select count(*) from cerata.cohorts c
                 join cerata.cohort_runs r on r.id = c.run_id and r.is_current),
    'modularity', (select modularity from cerata.cohort_runs where is_current),
    'checkin_coverage', (select round(avg((checked_in_at is not null)::int::numeric), 4)
                         from cerata.attendance),
    'avg_classes', (select round(avg(n), 2) from
                    (select count(*) as n from cerata.attendance group by person_id) s),
    'roster_rows', (select count(*) from cerata.attendance),
    'note', 'RSVP data (check-in coverage ~0.2%). Predicts who SIGNS UP; enjoyment = cohort reattendance to host/track, not confirmed presence. People are pseudonymized server-side.'
  ),
  'cohorts', coalesce((
    select jsonb_agg(jsonb_build_object(
      'idx', c.idx, 'label', c.label,
      'size', (select count(*) from cerata.cohort_members cm where cm.cohort_id = c.id),
      'tags', (select coalesce(jsonb_agg(jsonb_build_array(k, n)), '[]'::jsonb) from (
        select t.tag as k, count(*) as n
        from cerata.cohort_members cm
        join cerata.attendance a on a.person_id = cm.person_id
        join cerata.v_niche_events ne on ne.event_id = a.event_id
        join cerata.events e on e.id = a.event_id
        cross join lateral unnest(e.tags) as t(tag)
        where cm.cohort_id = c.id group by t.tag order by count(*) desc limit 5) s),
      'tracks', (select coalesce(jsonb_agg(jsonb_build_array(k, n)), '[]'::jsonb) from (
        select e.track as k, count(*) as n
        from cerata.cohort_members cm
        join cerata.attendance a on a.person_id = cm.person_id
        join cerata.v_niche_events ne on ne.event_id = a.event_id
        join cerata.events e on e.id = a.event_id
        where cm.cohort_id = c.id and e.track is not null
        group by e.track order by count(*) desc limit 3) s),
      'hosts', (select coalesce(jsonb_agg(jsonb_build_array(k, n)), '[]'::jsonb) from (
        select e.host as k, count(*) as n
        from cerata.cohort_members cm
        join cerata.attendance a on a.person_id = cm.person_id
        join cerata.v_niche_events ne on ne.event_id = a.event_id
        join cerata.events e on e.id = a.event_id
        where cm.cohort_id = c.id and e.host is not null and e.host <> ''
        group by e.host order by count(*) desc limit 3) s),
      'signature_classes', (select coalesce(jsonb_agg(k), '[]'::jsonb) from (
        select e.title as k, count(*) as n
        from cerata.cohort_members cm
        join cerata.attendance a on a.person_id = cm.person_id
        join cerata.v_niche_events ne on ne.event_id = a.event_id
        join cerata.events e on e.id = a.event_id
        where cm.cohort_id = c.id group by e.title order by count(*) desc limit 6) s),
      'members', (select coalesce(jsonb_agg(alias), '[]'::jsonb) from (
        select p.alias, count(a.event_id) as n
        from cerata.cohort_members cm
        join cerata.people p on p.id = cm.person_id
        left join cerata.attendance a on a.person_id = cm.person_id
        left join cerata.v_niche_events ne on ne.event_id = a.event_id
        where cm.cohort_id = c.id
        group by p.alias order by count(ne.event_id) desc limit 10) s)
    ) order by c.idx)
    from cerata.cohorts c
    join cerata.cohort_runs r on r.id = c.run_id and r.is_current
  ), '[]'::jsonb),
  'people', coalesce((
    select jsonb_agg(jsonb_build_object(
      'alias', alias, 'cohort', cohort_idx, 'n', n_classes) order by n_classes desc, alias)
    from cerata.v_person_stats where n_classes > 0
  ), '[]'::jsonb),
  'classes', coalesce((
    select jsonb_agg(jsonb_build_object(
      'ext_id', e.ext_id, 'title', e.title, 'track', e.track, 'host', e.host,
      'start', e.starts_at, 'n', s.attendee_count,
      'upcoming', e.starts_at > now()) order by s.attendee_count desc, e.title)
    from cerata.events e
    join cerata.v_event_stats s on s.event_id = e.id
  ), '[]'::jsonb)
)
$$;

create function public.cerata_person(p_alias text)
returns jsonb
language sql stable security definer set search_path = ''
as $$
select jsonb_build_object(
  'alias', p.alias,
  'cohort', pc.cohort_idx,
  'cohort_label', pc.cohort_label,
  'n_classes', (select count(*) from cerata.attendance a where a.person_id = p.id),
  'classes', coalesce((
    select jsonb_agg(jsonb_build_object('ext_id', ext_id, 'title', title)) from (
      select e.ext_id, e.title
      from cerata.attendance a
      join cerata.events e on e.id = a.event_id
      join cerata.v_event_stats s on s.event_id = e.id
      where a.person_id = p.id
      order by s.attendee_count asc limit 40) s
  ), '[]'::jsonb),
  'co_attendees', coalesce((
    select jsonb_agg(jsonb_build_array(alias, n)) from (
      select q.alias, ca.shared_n as n
      from (
        select person_b as other, shared_n from cerata.v_co_attendance where person_a = p.id
        union all
        select person_a as other, shared_n from cerata.v_co_attendance where person_b = p.id
      ) ca
      join cerata.people q on q.id = ca.other
      order by ca.shared_n desc limit 8) s
  ), '[]'::jsonb),
  'predicted_classes', coalesce((
    select jsonb_agg(jsonb_build_array(title, members)) from (
      select e.title, cc.members
      from cerata.v_cohort_class cc
      join cerata.events e on e.id = cc.event_id
      join cerata.v_event_stats s on s.event_id = cc.event_id
      where cc.cohort_idx = pc.cohort_idx
        and s.attendee_count <= 60
        and not exists (select 1 from cerata.attendance a
                        where a.person_id = p.id and a.event_id = cc.event_id)
      order by cc.members desc limit 8) s
  ), '[]'::jsonb),
  'signature', jsonb_build_object(
    'tracks', coalesce((select jsonb_agg(jsonb_build_array(k, n)) from (
      select e.track as k, count(*) as n from cerata.attendance a
      join cerata.events e on e.id = a.event_id
      where a.person_id = p.id and e.track is not null
      group by e.track order by count(*) desc limit 3) s), '[]'::jsonb),
    'tags', coalesce((select jsonb_agg(jsonb_build_array(k, n)) from (
      select t.tag as k, count(*) as n from cerata.attendance a
      join cerata.events e on e.id = a.event_id
      cross join lateral unnest(e.tags) as t(tag)
      where a.person_id = p.id
      group by t.tag order by count(*) desc limit 4) s), '[]'::jsonb),
    'hosts', coalesce((select jsonb_agg(jsonb_build_array(k, n)) from (
      select e.host as k, count(*) as n from cerata.attendance a
      join cerata.events e on e.id = a.event_id
      where a.person_id = p.id and e.host is not null and e.host <> ''
      group by e.host order by count(*) desc limit 3) s), '[]'::jsonb)
  )
)
from cerata.people p
left join cerata.v_person_cohort pc on pc.person_id = p.id
where p.alias = p_alias
$$;

create function public.cerata_class(p_ext_id text)
returns jsonb
language sql stable security definer set search_path = ''
as $$
select jsonb_build_object(
  'ext_id', e.ext_id, 'title', e.title, 'track', e.track, 'host', e.host,
  'tags', to_jsonb(e.tags), 'start', e.starts_at, 'end', e.ends_at,
  'upcoming', e.starts_at > now(),
  'attendee_count', (select attendee_count from cerata.v_event_stats where event_id = e.id),
  'cohort_mix', coalesce((
    select jsonb_agg(jsonb_build_array(cohort_idx, members) order by members desc)
    from cerata.v_cohort_class where event_id = e.id
  ), '[]'::jsonb),
  'attendees', coalesce((
    select jsonb_agg(alias) from (
      select p.alias from cerata.attendance a
      join cerata.people p on p.id = a.person_id
      where a.event_id = e.id order by p.alias limit 60) s
  ), '[]'::jsonb),
  'enjoyment', coalesce((
    select jsonb_build_object('host_return', host_return, 'track_return', track_return)
    from cerata.v_enjoyment where event_id = e.id
  ), jsonb_build_object('host_return', null, 'track_return', null))
)
from cerata.events e
where e.ext_id = p_ext_id
$$;

-- The attention market, cleared server-side. Each future time-slot with ≥2
-- candidate events is a market; events bid with the person's cohort affinity;
-- the slot clears to the top bid and reports the spread as opportunity cost.
create function public.cerata_market(p_alias text)
returns jsonb
language sql stable security definer set search_path = ''
as $$
with self as (
  select p.id, p.alias, pc.cohort_idx, pc.cohort_label
  from cerata.people p
  left join cerata.v_person_cohort pc on pc.person_id = p.id
  where p.alias = p_alias
), scored as (
  select e.ext_id, e.title, e.track, e.host, e.tags, e.starts_at,
         cerata.bid((select cohort_idx from self), e) as bid
  from cerata.events e
  where e.starts_at > now()
    and (select cohort_idx from self) is not null
    and not exists (
      select 1 from cerata.attendance a
      join cerata.events e2 on e2.id = a.event_id
      where a.person_id = (select id from self)
        and lower(e2.title) = lower(e.title))
), norm as (
  select greatest(max(bid), 0.0001) as max_bid from scored
), ranked as (
  select scored.*, row_number() over (partition by starts_at order by bid desc) as rk
  from scored
), slots as (
  select starts_at,
         jsonb_agg(jsonb_build_object(
           'ext_id', ext_id, 'title', title, 'track', track, 'host', host,
           'pct', round(bid / (select max_bid from norm) * 100))
           order by rk) as events,
         count(*)::int as n_events,
         round((max(bid) filter (where rk = 1)
              - coalesce(max(bid) filter (where rk = 2), 0))
              / (select max_bid from norm) * 100) as opportunity_cost
  from ranked
  group by starts_at
  having count(*) >= 2
)
select jsonb_build_object(
  'alias', (select alias from self),
  'cohort', (select cohort_idx from self),
  'cohort_label', (select cohort_label from self),
  'now', now(),
  'slots', coalesce((
    select jsonb_agg(jsonb_build_object(
      'start', starts_at, 'events', events, 'oc', opportunity_cost)
      order by starts_at)
    from slots
  ), '[]'::jsonb)
)
$$;
