-- cerata perception layer — Rose Glass reads of live language signals.
-- The structural invariant extends from names to words: RAW TEXT IS NEVER
-- STORED SERVER-SIDE. A signal row is metadata (source, window, content hash,
-- length); what persists is the PERCEPTION — per-lens dimensional readings
-- (Ψ ρ q f τ), the between-lens variance λ, and the Veritas flag. The
-- instrument keeps the reading, not the conversation.

create table cerata.signals (
  id            uuid primary key default gen_random_uuid(),
  person_id     uuid references cerata.people(id) on delete cascade,
  source        text not null check (source in ('telegram','network','geo','edgeos','manual')),
  provenance    cerata.provenance not null default 'stated',
  window_start  timestamptz,
  window_end    timestamptz,
  content_hash  text not null,
  char_count    int not null,
  created_at    timestamptz not null default now(),
  unique (person_id, source, content_hash)
);
comment on table cerata.signals is
  'A perceived language signal. Raw text never reaches this database — only its hash, length, and the lens readings derived from it on the operator''s machine.';
comment on column cerata.signals.provenance is
  'Language is stated signal by definition (etiquette-inflated). The Rose Glass read measures structure beneath the etiquette; it does not launder stated into revealed.';
comment on column cerata.signals.content_hash is
  'sha256 of the aggregated text. Dedupe key for re-perception; irreversible.';

create table cerata.lens_reads (
  id         uuid primary key default gen_random_uuid(),
  signal_id  uuid not null references cerata.signals(id) on delete cascade,
  lens       text not null,
  family     text not null check (family in ('google','anthropic')),
  psi        numeric not null,
  rho        numeric not null,
  q_raw      numeric not null,
  q_opt      numeric not null,
  f          numeric not null,
  tau        numeric not null,
  created_at timestamptz not null default now(),
  unique (signal_id, lens)
);
comment on table cerata.lens_reads is
  'One independent LLM perceiver''s read of one signal along five Rose Glass dimensions. Lenses are never averaged into a verdict; the gaps between them are the information.';
comment on column cerata.lens_reads.q_opt is
  'Emotional activation after Michaelis-Menten saturation with substrate inhibition — extreme states cannot amplify into dimensional readings.';

create table cerata.perceptions (
  signal_id        uuid primary key references cerata.signals(id) on delete cascade,
  lambda           jsonb not null,
  veritas          boolean not null default false,
  veritas_threshold numeric not null default 0.02,
  n_lenses         int not null,
  created_at       timestamptz not null default now()
);
comment on table cerata.perceptions is
  'Per-signal rollup: λ = per-dimension variance (σ²) across all lenses. Veritas is a REFUSAL mechanism — true only when every dimension''s σ² is under threshold; otherwise the instrument reports its silence honestly.';
comment on column cerata.perceptions.lambda is
  'jsonb {psi,rho,q,f,tau} → σ² across lenses. Belongs to no single lens. The moiré is the finding.';

alter table cerata.signals     enable row level security;
alter table cerata.lens_reads  enable row level security;
alter table cerata.perceptions enable row level security;

-- Per-person essence: every lens read + λ rollup, most recent signal per source.
create view cerata.v_person_essence as
select s.person_id, s.id as signal_id, s.source, s.window_start, s.window_end,
       s.char_count, s.created_at,
       p.lambda, p.veritas, p.n_lenses
from cerata.signals s
join cerata.perceptions p on p.signal_id = s.id;

-- Essence RPC: a person's Rose Glass reads, raw per lens, never synthesized.
create function public.cerata_essence(p_alias text)
returns jsonb
language sql stable security definer set search_path = ''
as $$
select jsonb_build_object(
  'alias', pe.alias,
  'signals', coalesce((
    select jsonb_agg(jsonb_build_object(
      'signal_id', s.id,
      'source', s.source,
      'window_start', s.window_start,
      'window_end', s.window_end,
      'char_count', s.char_count,
      'perceived_at', s.created_at,
      'lambda', pc.lambda,
      'veritas', pc.veritas,
      'veritas_threshold', pc.veritas_threshold,
      'reads', (
        select jsonb_agg(jsonb_build_object(
          'lens', lr.lens, 'family', lr.family,
          'psi', lr.psi, 'rho', lr.rho, 'q_raw', lr.q_raw,
          'q_opt', lr.q_opt, 'f', lr.f, 'tau', lr.tau) order by lr.lens)
        from cerata.lens_reads lr where lr.signal_id = s.id
      )) order by s.created_at desc)
    from cerata.signals s
    join cerata.perceptions pc on pc.signal_id = s.id
    where s.person_id = pe.id
  ), '[]'::jsonb)
)
from cerata.people pe
where pe.alias = p_alias
$$;

-- All perceived people (for the overview essence wall).
create function public.cerata_essences()
returns jsonb
language sql stable security definer set search_path = ''
as $$
select coalesce(jsonb_agg(row order by row -> 'latest' ->> 'perceived_at' desc), '[]'::jsonb)
from (
  select jsonb_build_object(
    'alias', pe.alias,
    'cohort', pc.cohort_idx,
    'n_signals', count(*),
    'veritas_n', count(*) filter (where e.veritas),
    'latest', (
      select jsonb_build_object(
        'signal_id', s2.id, 'source', s2.source, 'lambda', p2.lambda,
        'veritas', p2.veritas, 'perceived_at', s2.created_at,
        'reads', (
          select jsonb_agg(jsonb_build_object(
            'lens', lr.lens, 'family', lr.family,
            'psi', lr.psi, 'rho', lr.rho, 'q_opt', lr.q_opt,
            'f', lr.f, 'tau', lr.tau) order by lr.lens)
          from cerata.lens_reads lr where lr.signal_id = s2.id))
      from cerata.signals s2
      join cerata.perceptions p2 on p2.signal_id = s2.id
      where s2.person_id = pe.id
      order by s2.created_at desc limit 1
    )
  ) as row
  from cerata.v_person_essence e
  join cerata.people pe on pe.id = e.person_id
  left join cerata.v_person_cohort pc on pc.person_id = pe.id
  group by pe.id, pe.alias, pc.cohort_idx
) t
$$;
