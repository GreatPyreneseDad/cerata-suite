-- cerata cultural-lens layer.
-- A cultural lens is an engineered PERSPECTIVE, not a demographic label. Each
-- person is read through every lens; the lens with the lowest λ (best fit) is
-- their NATIVE lens. The payload is the inverse: persistently high λ across all
-- lenses = a person the instrument's worldview cannot natively see, and a lens
-- whose profile doesn't match what the village actually programs = a structural
-- blind spot. Legibility is a property of the INSTRUMENT, never a stamp on a
-- person — the roseglassdata.com discipline applied to perception itself.

create table cerata.cultural_lenses (
  id            uuid primary key default gen_random_uuid(),
  slug          text not null unique,
  label         text not null,
  lens_group    text not null,          -- builder | somatic | esoteric | social | creative | knowledge | role | age | shared
  profile       jsonb not null default '{}'::jsonb,  -- {tag|track|host -> weight}; transparent and editable
  needs_language boolean not null default false,      -- age/shared registers: require perceived language, not RSVP behavior
  supply_coverage numeric,              -- fraction of village programming matching this lens (0..1); low = blind spot
  created_at    timestamptz not null default now()
);
comment on table cerata.cultural_lenses is
  'Engineered cultural PERSPECTIVES. profile is the lens calibration over observable features; supply_coverage measures how much of the actual event programming this culture is served by — a structural, supply-side legibility signal, never a demographic claim.';
comment on column cerata.cultural_lenses.needs_language is
  'true for age/shared register lenses: fit requires perceived language (deep-dive), not RSVP behavior. The strawman test computes content lenses over attendance.';
comment on column cerata.cultural_lenses.supply_coverage is
  'Share of village programming matching this lens. Low coverage = the village does not program for this culture = the instrument''s blind spot is supply-side, not a property of any person.';

create table cerata.cultural_reads (
  person_id    uuid not null references cerata.people(id) on delete cascade,
  lens_id      uuid not null references cerata.cultural_lenses(id) on delete cascade,
  fit          numeric not null,        -- cosine(person attendance signature, lens profile) 0..1
  lambda       numeric not null,        -- 1 - fit; low = native
  is_native    boolean not null default false,
  is_bicultural boolean not null default false,  -- within ε of the native lens
  created_at   timestamptz not null default now(),
  primary key (person_id, lens_id)
);
comment on table cerata.cultural_reads is
  'Per (person, lens) fit. native = argmin λ; bicultural = any lens within ε of the min. legibility(person) = min λ across lenses — high means no lens reads them, the instrument''s blind spot made personal.';

alter table cerata.cultural_lenses enable row level security;
alter table cerata.cultural_reads  enable row level security;

-- A person's legibility: their best (min) λ and which lens achieves it.
create view cerata.v_legibility as
select cr.person_id,
       min(cr.lambda) as best_lambda,
       (array_agg(cl.label order by cr.lambda))[1] as native_label,
       (array_agg(cl.slug  order by cr.lambda))[1] as native_slug
from cerata.cultural_reads cr
join cerata.cultural_lenses cl on cl.id = cr.lens_id
group by cr.person_id;

-- Per-lens rollup: how many people are native to it, mean residual λ of its
-- natives, its supply coverage. A lens with few natives + high residual +
-- low supply = the village's blind spot.
create view cerata.v_lens_stats as
select cl.id, cl.slug, cl.label, cl.lens_group, cl.needs_language, cl.supply_coverage,
       count(*) filter (where cr.is_native) as natives,
       round(avg(cr.lambda) filter (where cr.is_native), 4) as native_mean_lambda,
       round(avg(cr.fit), 4) as mean_fit
from cerata.cultural_lenses cl
left join cerata.cultural_reads cr on cr.lens_id = cl.id
group by cl.id, cl.slug, cl.label, cl.lens_group, cl.needs_language, cl.supply_coverage;

-- Cultures overview RPC: every lens with its blind-spot signals, ranked.
create function public.cerata_cultures()
returns jsonb
language sql stable security definer set search_path = ''
as $$
select jsonb_build_object(
  'meta', jsonb_build_object(
    'lenses', (select count(*) from cerata.cultural_lenses),
    'read_people', (select count(distinct person_id) from cerata.cultural_reads),
    'mean_legibility', (select round(avg(best_lambda), 4) from cerata.v_legibility),
    'illegible', (select count(*) from cerata.v_legibility where best_lambda > 0.6),
    'note', 'Legibility is a property of the instrument. High λ = the village''s lens panel cannot natively read this person; low supply_coverage = the village does not program for this culture. Neither is a demographic label.'
  ),
  'lenses', coalesce((
    select jsonb_agg(jsonb_build_object(
      'slug', slug, 'label', label, 'group', lens_group,
      'needs_language', needs_language, 'supply_coverage', supply_coverage,
      'natives', natives, 'native_mean_lambda', native_mean_lambda, 'mean_fit', mean_fit,
      'blind_spot', case when needs_language then null
        else round((1 - coalesce(supply_coverage, 0)) * (1 - coalesce(mean_fit, 0)), 4) end)
      order by needs_language,
        case when needs_language then null
          else (1 - coalesce(supply_coverage, 0)) * (1 - coalesce(mean_fit, 0)) end desc nulls last)
    from cerata.v_lens_stats
  ), '[]'::jsonb)
)
$$;

-- A person's full culture spectrum: every lens by λ, native + bicultural flags.
create function public.cerata_person_cultures(p_alias text)
returns jsonb
language sql stable security definer set search_path = ''
as $$
select jsonb_build_object(
  'alias', pe.alias,
  'native', (select cl.label from cerata.cultural_reads cr
             join cerata.cultural_lenses cl on cl.id = cr.lens_id
             where cr.person_id = pe.id and cr.is_native limit 1),
  'legibility', (select round(best_lambda, 4) from cerata.v_legibility where person_id = pe.id),
  'spectrum', coalesce((
    select jsonb_agg(jsonb_build_object(
      'slug', cl.slug, 'label', cl.label, 'group', cl.lens_group,
      'fit', round(cr.fit, 4), 'lambda', round(cr.lambda, 4),
      'native', cr.is_native, 'bicultural', cr.is_bicultural) order by cr.lambda)
    from cerata.cultural_reads cr
    join cerata.cultural_lenses cl on cl.id = cr.lens_id
    where cr.person_id = pe.id
  ), '[]'::jsonb)
)
from cerata.people pe
where pe.alias = p_alias
$$;
