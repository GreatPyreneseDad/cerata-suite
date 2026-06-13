// cerata-refresh — the live loop. Pulls fresh EdgeOS village activity (events +
// rosters) on a schedule and upserts the base facts; because the analytics are
// SQL views, the market / cohort-mix / enjoyment / predictions all go current
// the instant these tables update.
//
// Secrets (EdgeOS key, pseudonymization salt, shared token) are read from the
// Supabase Vault over the DB connection — they never live in this source, in
// function env, or in the browser. People are pseudonymized server-side with the
// same salt as the rest of cerata, so a refreshed RSVP lands on the same row.
import postgres from 'npm:postgres@3.4.5'

const POPUP = '43746fd0-bce2-472b-93e4-a438177b2dff'
const BASE = 'https://api.edgeos.world/api/v1'
const POPUP_END = '2026-06-28T07:00:00Z'

const ADJ = ["amber","ashen","blue","bold","briar","bright","calm","cedar","civic","clear","coral","dapper","dawn","deep","dusk","eager","early","ember","fable","fern","flint","gentle","gilded","glass","green","hazel","hidden","indigo","iron","ivory","jade","keen","late","lunar","mellow","misty","noble","north","ochre","opal","pale","quiet","rose","rust","sable","salt","silver","slate","still","storm","swift","tidal","umber","velvet","violet","warm","wild","winter","woven","zephyr"]
const CRE = ["heron","otter","fox","wren","lynx","seal","crane","finch","badger","ibis","marten","osprey","plover","raven","sable","tern","vole","walrus","egret","stoat","curlew","dipper","ermine","fulmar","gannet","godwit","grebe","jay","kite","knot","lapwing","loon","merlin","murre","newt","oriole","pika","pipit","puffin","quail","redstart","sanderling","shrike","siskin","skua","smew","snipe","swift","teal","thrush"]

async function sha256hex(s: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s))
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('')
}
function baseAlias(h: string): string {
  const n = parseInt(h.slice(0, 12), 16)
  return ADJ[n % ADJ.length] + '-' + CRE[Math.floor(n / ADJ.length) % CRE.length]
}

async function edgeGet(key: string, path: string, params: Record<string, string>): Promise<any> {
  const qs = new URLSearchParams(params).toString()
  for (let a = 0; a < 4; a++) {
    const r = await fetch(`${BASE}${path}?${qs}`, { headers: { Authorization: 'Bearer ' + key } })
    if (r.ok) return r.json()
    if (r.status === 429) { await new Promise(s => setTimeout(s, 2000)); continue }
    if (r.status >= 500) { await new Promise(s => setTimeout(s, 1500 * (a + 1))); continue }
    return null
  }
  return null
}

Deno.serve(async (req) => {
  const sql = postgres(Deno.env.get('SUPABASE_DB_URL')!, { prepare: false })
  let logId: string | null = null
  try {
    const sec = await sql`select name, decrypted_secret from vault.decrypted_secrets
                          where name in ('cerata_edgeos_key','cerata_salt','cerata_ingest_token')`
    const S: Record<string, string> = {}
    for (const r of sec) S[r.name] = r.decrypted_secret
    const token = req.headers.get('x-ingest-token')
    if (!S.cerata_ingest_token || token !== S.cerata_ingest_token)
      return new Response('forbidden', { status: 403 })
    if (!S.cerata_edgeos_key) return Response.json({ ok: false, error: 'no edgeos key in vault' }, { status: 500 })

    const url = new URL(req.url)
    const source = url.searchParams.get('source') ?? 'edgeos-cron'
    // rolling window: recent + all upcoming = the live edge of village activity
    const days = parseInt(url.searchParams.get('days') ?? '3')
    const startAfter = new Date(Date.now() - days * 86400000).toISOString()

    const [log] = await sql`insert into cerata.refresh_log (source) values (${source}) returning id`
    logId = log.id

    // 1) events in window (paginate, dedupe occurrences -> base event)
    const events: any[] = []
    for (let skip = 0; ; skip += 100) {
      const d = await edgeGet(S.cerata_edgeos_key, '/events/portal/events', {
        popup_id: POPUP, event_status: 'published', start_after: startAfter,
        start_before: POPUP_END, limit: '100', skip: String(skip),
      })
      const res = d?.results ?? []
      events.push(...res)
      if (res.length < 100) break
    }
    const uniq = new Map<string, any>()
    for (const e of events) if (!uniq.has(e.id)) uniq.set(e.id, e)

    // upsert events
    let evN = 0
    const evRows = [...uniq.values()].map(e => ({
      ext_id: e.id, title: e.title ?? 'untitled', track: e.track_title ?? null,
      host: e.host_display_name || null, tags: e.tags ?? [],
      starts_at: e.start_time ?? null, ends_at: e.end_time ?? null,
    }))
    for (let i = 0; i < evRows.length; i += 100) {
      const b = evRows.slice(i, i + 100)
      await sql`insert into cerata.events ${sql(b, 'ext_id','title','track','host','tags','starts_at','ends_at')}
                on conflict (ext_id) do update set title=excluded.title, track=excluded.track,
                  host=excluded.host, tags=excluded.tags, starts_at=excluded.starts_at, ends_at=excluded.ends_at`
      evN += b.length
    }

    // 2) rosters for those events (bounded concurrency)
    const ids = [...uniq.keys()]
    const rosters: Record<string, any[]> = {}
    const CONC = 8
    for (let i = 0; i < ids.length; i += CONC) {
      await Promise.all(ids.slice(i, i + CONC).map(async eid => {
        const rows: any[] = []
        for (let skip = 0; ; skip += 100) {
          const d = await edgeGet(S.cerata_edgeos_key, '/event-participants/portal/participants',
            { event_id: eid, limit: '100', skip: String(skip) })
          const res = d?.results ?? []
          rows.push(...res)
          if (res.length < 100) break
        }
        rosters[eid] = rows
      }))
    }

    // 3) hash people, mint aliases for new ones, upsert people + attendance
    const taken = new Set<string>((await sql`select alias from cerata.people`).map((r: any) => r.alias))
    const hashByPid = new Map<string, string>()
    const aliasByHash = new Map<string, string>()
    // dedupe by (person, event): a person can appear on a roster multiple times
    // (recurring occurrences); collapse to one row, preferring a check-in.
    const attByKey = new Map<string, any>()
    let attSeen = 0, newPeople = 0
    for (const [eid, rows] of Object.entries(rosters)) {
      for (const r of rows as any[]) {
        const pid = r.profile_id
        if (!pid) continue
        attSeen++
        let h = hashByPid.get(pid)
        if (!h) { h = await sha256hex(S.cerata_salt + pid); hashByPid.set(pid, h) }
        if (!aliasByHash.has(h)) {
          let a = baseAlias(h)
          if (taken.has(a)) a = a + '-' + h.slice(0, 4)
          taken.add(a); aliasByHash.set(h, a)
        }
        const key = h + '|' + eid
        const prev = attByKey.get(key)
        const row = {
          ext_hash: h, ext_id: eid,
          provenance: r.check_time ? 'checkin' : 'rsvp',
          rsvp_status: r.status ?? null,
          registered_at: r.registered_at ?? null,
          checked_in_at: r.check_time ?? null,
        }
        if (!prev || (row.checked_in_at && !prev.checked_in_at)) attByKey.set(key, row)
      }
    }
    const attRows = [...attByKey.values()]
    // people first (FK), then attendance
    const peopleRows = [...aliasByHash.entries()].map(([h, a]) => ({ ext_hash: h, alias: a }))
    for (let i = 0; i < peopleRows.length; i += 500) {
      const b = peopleRows.slice(i, i + 500)
      const before = (await sql`select count(*)::int as c from cerata.people`)[0].c
      await sql`insert into cerata.people ${sql(b, 'ext_hash', 'alias')} on conflict (ext_hash) do nothing`
      const after = (await sql`select count(*)::int as c from cerata.people`)[0].c
      newPeople += after - before
    }
    for (let i = 0; i < attRows.length; i += 500) {
      const b = attRows.slice(i, i + 500)
      await sql`insert into cerata.attendance (person_id, event_id, provenance, rsvp_status, registered_at, checked_in_at)
                select p.id, e.id, v.provenance::cerata.provenance, v.rsvp_status,
                       v.registered_at::timestamptz, v.checked_in_at::timestamptz
                from jsonb_to_recordset(${sql.json(b)})
                  as v(ext_hash text, ext_id text, provenance text, rsvp_status text, registered_at text, checked_in_at text)
                join cerata.people p on p.ext_hash = v.ext_hash
                join cerata.events e on e.ext_id = v.ext_id
                on conflict (person_id, event_id) do update set
                  provenance = excluded.provenance, checked_in_at = excluded.checked_in_at`
    }

    await sql`update cerata.refresh_log set finished_at = now(), ok = true,
              events_seen = ${evN}, attendance_seen = ${attSeen}, new_people = ${newPeople},
              note = ${'window ' + days + 'd'} where id = ${logId}`
    return Response.json({ ok: true, events: evN, attendance: attSeen, new_people: newPeople })
  } catch (e) {
    if (logId) await sql`update cerata.refresh_log set finished_at = now(), ok = false, note = ${String(e)} where id = ${logId}`
    return Response.json({ ok: false, error: String(e) }, { status: 500 })
  } finally {
    await sql.end()
  }
})
