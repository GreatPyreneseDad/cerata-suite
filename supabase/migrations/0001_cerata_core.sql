-- cerata core schema — revealed-behavior facts, normalized.
-- Schema-semantics discipline per roseglassdata.com: every column states its
-- collection method, its NULL semantics, and any proxy risk. The `cerata`
-- schema is NOT exposed through PostgREST; all access flows through
-- security-definer RPCs in `public` that return pseudonymous reads only.

create schema if not exists cerata;

create type cerata.provenance as enum ('rsvp', 'checkin', 'stated', 'imported');
comment on type cerata.provenance is
  'Collection method for a behavioral fact. rsvp = signed up; checkin = scanned in (highest trust); stated = self-reported (etiquette-inflated, lowest trust); imported = bulk load of unknown method.';

create table cerata.people (
  id         uuid primary key default gen_random_uuid(),
  ext_hash   text not null unique,
  alias      text not null unique,
  created_at timestamptz not null default now()
);
comment on table cerata.people is
  'Attendees, PII-minimized. Only a salted hash of the source profile id and a deterministic pseudonym are stored; legal names never leave the operator''s machine.';
comment on column cerata.people.ext_hash is
  'sha256(local_salt || source_profile_id). Re-ingest join key; irreversible without the operator-held salt.';
comment on column cerata.people.alias is
  'Deterministic pseudonym minted at ingest. Semantic type: display identity, not legal identity.';

create table cerata.events (
  id         uuid primary key default gen_random_uuid(),
  ext_id     text not null unique,
  title      text not null,
  track      text,
  host       text,
  tags       text[] not null default '{}',
  starts_at  timestamptz,
  ends_at    timestamptz,
  created_at timestamptz not null default now()
);
comment on table cerata.events is 'Published calendar events (public information at source).';
comment on column cerata.events.track is
  'NULL semantics: "no track assigned at source" (~43% of events), not "unknown". Proxy risk: track correlates strongly with cohort membership — never treat as a neutral feature.';
comment on column cerata.events.host is
  'Host display name as published on the public calendar. NULL = source omitted it.';
comment on column cerata.events.starts_at is
  'Events with starts_at > now() are the attention market''s inventory; past events are the evidence base.';

create table cerata.attendance (
  person_id     uuid not null references cerata.people(id) on delete cascade,
  event_id      uuid not null references cerata.events(id) on delete cascade,
  provenance    cerata.provenance not null default 'rsvp',
  rsvp_status   text,
  registered_at timestamptz,
  checked_in_at timestamptz,
  primary key (person_id, event_id)
);
comment on table cerata.attendance is
  'Revealed-behavior facts. The suite''s thesis: measure what gets done, not what gets said — every downstream read derives from this table.';
comment on column cerata.attendance.checked_in_at is
  'NULL semantics: "no check-in record" (scanner coverage ~0.25% at source), NOT "did not attend". Never compute attendance rates from this column alone.';
comment on column cerata.attendance.registered_at is
  'When the RSVP was placed. NULL = source row predates registration timestamps.';

create index attendance_event_idx on cerata.attendance (event_id);

create table cerata.cohort_runs (
  id          uuid primary key default gen_random_uuid(),
  algorithm   text not null default 'louvain-niche',
  params      jsonb not null default '{}'::jsonb,
  modularity  numeric,
  is_current  boolean not null default false,
  created_at  timestamptz not null default now()
);
comment on table cerata.cohort_runs is
  'One row per clustering run. Cohorts are versioned by run so reads are reproducible; exactly one run is current.';
comment on column cerata.cohort_runs.modularity is
  'Louvain modularity Q of the run (~0.32 on real data). Stated in the UI — a dominant communal track can mask finer cohorts.';
create unique index cohort_runs_current_uniq on cerata.cohort_runs (is_current) where is_current;

create table cerata.cohorts (
  id     uuid primary key default gen_random_uuid(),
  run_id uuid not null references cerata.cohort_runs(id) on delete cascade,
  idx    int  not null,
  label  text not null,
  unique (run_id, idx)
);

create table cerata.cohort_members (
  cohort_id uuid not null references cerata.cohorts(id) on delete cascade,
  person_id uuid not null references cerata.people(id) on delete cascade,
  primary key (cohort_id, person_id)
);

-- Deny-by-default: the cerata schema is not in PostgREST's exposed schemas and
-- carries no policies. Reads happen exclusively through public RPCs.
alter table cerata.people         enable row level security;
alter table cerata.events         enable row level security;
alter table cerata.attendance     enable row level security;
alter table cerata.cohort_runs    enable row level security;
alter table cerata.cohorts        enable row level security;
alter table cerata.cohort_members enable row level security;
