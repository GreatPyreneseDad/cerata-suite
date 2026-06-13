-- cerata liveness — heartbeat + pulse.
-- The live loop refreshes base facts (events, attendance) on a schedule; because
-- the analytics are SQL views, market/cohort-mix/enjoyment/predictions go current
-- the instant the base tables update. This layer records each refresh and exposes
-- a cheap freshness probe for the frontend to poll.

create table cerata.refresh_log (
  id           uuid primary key default gen_random_uuid(),
  source       text not null,             -- edgeos-cron | edgeos-manual | local | perception | cultures
  started_at   timestamptz not null default now(),
  finished_at  timestamptz,
  ok           boolean,
  events_seen  int,
  attendance_seen int,
  new_people   int,
  note         text
);
comment on table cerata.refresh_log is
  'One row per refresh pass. The site reads the latest ok=true row as "last updated"; new village activity (events, RSVPs) lands through these passes.';

alter table cerata.refresh_log enable row level security;

-- Cheap freshness probe — what the frontend polls every minute.
create function public.cerata_pulse()
returns jsonb
language sql stable security definer set search_path = ''
as $$
select jsonb_build_object(
  'now', now(),
  'last_refresh', (select finished_at from cerata.refresh_log where ok order by finished_at desc nulls last limit 1),
  'last_source', (select source from cerata.refresh_log where ok order by finished_at desc nulls last limit 1),
  'people', (select count(*) from cerata.people),
  'events', (select count(*) from cerata.events),
  'upcoming', (select count(*) from cerata.events where starts_at > now()),
  'attendance', (select count(*) from cerata.attendance),
  'live_now', (select count(*) from cerata.events where now() between starts_at and coalesce(ends_at, starts_at + interval '2 hours')),
  'next_event', (select jsonb_build_object('title', title, 'start', starts_at, 'track', track)
                 from cerata.events where starts_at > now() order by starts_at limit 1)
)
$$;
comment on function public.cerata_pulse is 'Lightweight liveness probe: freshness + live counts + the next event on the calendar.';