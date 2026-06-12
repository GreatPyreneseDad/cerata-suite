// cerata-ingest — token-protected bulk loader for the cerata schema.
// Accepts structured JSON batches (never raw SQL) and writes through a direct
// Postgres connection. The token is rotated per deployment; rotate or stub
// this function out when an ingest session is done.
import postgres from 'npm:postgres@3.4.5'

const TOKEN = Deno.env.get('CERATA_INGEST_TOKEN') ?? ''

Deno.serve(async (req) => {
  if (req.method !== 'POST') return new Response('method not allowed', { status: 405 })
  if (!TOKEN || req.headers.get('x-ingest-token') !== TOKEN) return new Response('forbidden', { status: 403 })

  const sql = postgres(Deno.env.get('SUPABASE_DB_URL')!, { prepare: false })
  try {
    const body = await req.json()
    let n = 0
    if (body.kind === 'people') {
      for (let i = 0; i < body.rows.length; i += 500) {
        const b = body.rows.slice(i, i + 500)
        await sql`insert into cerata.people ${sql(b, 'ext_hash', 'alias')}
                  on conflict (ext_hash) do nothing`
        n += b.length
      }
    } else if (body.kind === 'events') {
      for (let i = 0; i < body.rows.length; i += 200) {
        const b = body.rows.slice(i, i + 200)
        await sql`insert into cerata.events ${sql(b, 'ext_id', 'title', 'track', 'host', 'tags', 'starts_at', 'ends_at')}
                  on conflict (ext_id) do update set
                    title = excluded.title, track = excluded.track, host = excluded.host,
                    tags = excluded.tags, starts_at = excluded.starts_at, ends_at = excluded.ends_at`
        n += b.length
      }
    } else if (body.kind === 'attendance') {
      for (let i = 0; i < body.rows.length; i += 500) {
        const b = body.rows.slice(i, i + 500)
        await sql`insert into cerata.attendance (person_id, event_id, provenance, rsvp_status, registered_at, checked_in_at)
                  select p.id, e.id, v.provenance::cerata.provenance, v.rsvp_status,
                         v.registered_at::timestamptz, v.checked_in_at::timestamptz
                  from jsonb_to_recordset(${sql.json(b)})
                    as v(ext_hash text, ext_id text, provenance text, rsvp_status text,
                         registered_at text, checked_in_at text)
                  join cerata.people p on p.ext_hash = v.ext_hash
                  join cerata.events e on e.ext_id = v.ext_id
                  on conflict (person_id, event_id) do update set
                    provenance = excluded.provenance, checked_in_at = excluded.checked_in_at`
        n += b.length
      }
    } else if (body.kind === 'cohorts') {
      const run = body.run
      await sql`update cerata.cohort_runs set is_current = false where is_current`
      const [r] = await sql`insert into cerata.cohort_runs (algorithm, params, modularity, is_current)
                            values ('louvain-niche', ${run.params}, ${run.modularity}, true)
                            returning id`
      for (const c of run.cohorts) {
        const [co] = await sql`insert into cerata.cohorts (run_id, idx, label)
                               values (${r.id}, ${c.idx}, ${c.label}) returning id`
        for (let i = 0; i < c.members.length; i += 500) {
          const hashes = c.members.slice(i, i + 500)
          await sql`insert into cerata.cohort_members (cohort_id, person_id)
                    select ${co.id}, p.id from cerata.people p
                    where p.ext_hash in ${sql(hashes)}
                    on conflict do nothing`
        }
        n += 1
      }
    } else if (body.kind === 'verify') {
      const r = await sql`select
        (select count(*)::int from cerata.people) as people,
        (select count(*)::int from cerata.events) as events,
        (select count(*)::int from cerata.attendance) as attendance,
        (select count(*)::int from cerata.cohorts c join cerata.cohort_runs cr on cr.id = c.run_id and cr.is_current) as cohorts,
        (select count(*)::int from cerata.cohort_members) as members,
        (select count(*)::int from cerata.events where starts_at > now()) as upcoming,
        (select count(*)::int from cerata.attendance where checked_in_at is not null) as checkins`
      return Response.json(r[0])
    } else {
      return Response.json({ ok: false, error: 'unknown kind' }, { status: 400 })
    }
    return Response.json({ ok: true, n })
  } catch (e) {
    return Response.json({ ok: false, error: String(e) }, { status: 500 })
  } finally {
    await sql.end()
  }
})
