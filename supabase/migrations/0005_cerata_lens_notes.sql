-- Per-dimension interpretive notes from each lens. Tradeoff stated plainly:
-- notes are the instrument's language about the signal and can paraphrase its
-- content. They are interpretations, not transcripts — but treat them as
-- sensitive. Omit at ingest (notes off) for stricter deployments.
alter table cerata.lens_reads add column notes jsonb;
comment on column cerata.lens_reads.notes is
  'jsonb {psi,rho,q,f,tau} -> one-line lens interpretation. May paraphrase signal content; sensitive. NULL = ingested with notes off.';

-- Re-create cerata_essence to surface notes alongside each lens read.
create or replace function public.cerata_essence(p_alias text)
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
          'q_opt', lr.q_opt, 'f', lr.f, 'tau', lr.tau,
          'notes', lr.notes) order by lr.lens)
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
