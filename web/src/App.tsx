import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Bootstrap, Cohort, fetchBootstrap, fetchClass, fetchMarket, fetchPerson,
  ClassRead, MarketRead, PersonRead, cohortColor, fmtTime, lastLatency, Pair,
} from './lib/api'
import { EssenceView, EssenceWall } from './Essence'

type Route =
  | { v: 'overview' }
  | { v: 'person'; alias: string }
  | { v: 'class'; id: string }
  | { v: 'cohort'; idx: number }
  | { v: 'market'; alias?: string }
  | { v: 'essences' }
  | { v: 'essence'; alias: string }

function parseHash(): Route {
  const h = decodeURIComponent(location.hash.replace(/^#/, ''))
  if (h.startsWith('person=')) return { v: 'person', alias: h.slice(7) }
  if (h.startsWith('class=')) return { v: 'class', id: h.slice(6) }
  if (h.startsWith('cohort=')) return { v: 'cohort', idx: +h.slice(7) }
  if (h.startsWith('essence=')) return { v: 'essence', alias: h.slice(8) }
  if (h === 'essences') return { v: 'essences' }
  if (h.startsWith('market')) return { v: 'market', alias: h.includes('=') ? h.split('=')[1] : undefined }
  return { v: 'overview' }
}
const go = (h: string) => { location.hash = h }

/* ---------- small pieces ---------- */

function Num({ to, decimals = 0 }: { to: number; decimals?: number }) {
  const [n, setN] = useState(0)
  useEffect(() => {
    let raf = 0
    const t0 = performance.now()
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / 900)
      setN(to * (1 - Math.pow(1 - p, 3)))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [to])
  return <>{n.toFixed(decimals)}</>
}

const Chips = ({ items, onClick }: { items: Pair[]; onClick?: (k: string) => void }) =>
  items?.length ? (
    <div className="chips">
      {items.map(([t, n]) => (
        <button key={t} className={'chip' + (onClick ? ' click' : '')} onClick={onClick && (() => onClick(t))} disabled={!onClick}>
          {t}<span className="n">{n}</span>
        </button>
      ))}
    </div>
  ) : <span className="empty" style={{ padding: 0 }}>—</span>

function Spinner({ label }: { label: string }) {
  return <div className="spinner"><div className="ring" /> {label}</div>
}

/* Deterministic cohort constellation — every clustered member is a star. */
function Constellation({ cohorts, onPick }: { cohorts: Cohort[]; onPick: (i: number) => void }) {
  const W = 560, H = 300
  const dots = useMemo(() => {
    const out: { x: number; y: number; c: number; key: string }[] = []
    cohorts.forEach((c, ci) => {
      const ang = (ci / cohorts.length) * Math.PI * 2 - Math.PI / 2
      const cx = W / 2 + Math.cos(ang) * 175
      const cy = H / 2 + Math.sin(ang) * 95
      for (let m = 0; m < c.size; m++) {
        // hash-ish deterministic scatter
        const a = ((m * 2654435761) % 360) * (Math.PI / 180)
        const r = 12 + ((m * 40503) % 1000) / 1000 * (26 + c.size * 0.55)
        out.push({ x: cx + Math.cos(a) * r * 1.5, y: cy + Math.sin(a) * r * 0.75, c: ci, key: ci + '-' + m })
      }
    })
    return out
  }, [cohorts])
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="constellation">
      {dots.map(d => (
        <circle key={d.key} cx={d.x} cy={d.y} r={3.2} fill={cohortColor(d.c)} opacity={0.78}
          onClick={() => onPick(d.c)}>
          <title>{cohorts[d.c].label} · {cohorts[d.c].size} people</title>
        </circle>
      ))}
      {cohorts.map((c, ci) => {
        const ang = (ci / cohorts.length) * Math.PI * 2 - Math.PI / 2
        const cx = W / 2 + Math.cos(ang) * 175
        const cy = H / 2 + Math.sin(ang) * 95
        return (
          <text key={ci} x={cx} y={cy + (Math.sin(ang) > 0.6 ? 62 : -48)} textAnchor="middle"
            fill="#9aa3b8" fontSize="10" fontFamily="SF Mono, monospace" style={{ cursor: 'pointer' }}
            onClick={() => onPick(ci)}>
            {c.label.split(' · ')[0]} · {c.size}
          </text>
        )
      })}
    </svg>
  )
}

/* ---------- views ---------- */

function Overview({ boot }: { boot: Bootstrap }) {
  const m = boot.meta
  const top = boot.classes.filter(c => !c.upcoming).slice(0, 9)
  return (
    <>
      <div className="hero">
        <h2>Stop trusting what gets <em>said</em>.<br />Measure what gets <em>done</em>.</h2>
        <p className="lede">
          cerata reads a community through revealed behavior — {m.roster_rows.toLocaleString()} RSVPs across {m.classes} events,
          clustered into {m.cohorts} behavioral cohorts — then prices everyone's finite attention in a live market.
          Computed server-side in Postgres, on Supabase, from pseudonymized facts.
        </p>
        <div className="loop">
          <span className="step"><b>PERCEIVE</b> read the room</span><span className="arrow">→</span>
          <span className="step"><b>PREDICT</b> cohort inference</span><span className="arrow">→</span>
          <span className="step"><b>PRICE</b> attention market</span><span className="arrow">→</span>
          <span className="step"><b>SETTLE</b> revealed behavior</span>
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat"><b><Num to={m.people} /></b><span>people</span></div>
        <div className="stat"><b><Num to={m.roster_rows} /></b><span>behavior facts</span></div>
        <div className="stat"><b className="accent"><Num to={m.cohorts} /></b><span>cohorts</span></div>
        <div className="stat"><b><Num to={m.modularity} decimals={3} /></b><span>modularity q</span></div>
        <div className="stat"><b><Num to={m.upcoming} /></b><span>market inventory</span></div>
      </div>

      <div className="card">
        <h3>The cohort constellation</h3>
        <div className="sub">every dot is a person, clustered by who they actually share small rooms with — Louvain on niche co-attendance</div>
        <Constellation cohorts={boot.cohorts} onPick={i => go('cohort=' + i)} />
      </div>

      <div className="grid2">
        <div className="card">
          <h3>Cohorts</h3>
          <div className="sub">labeled by what binds them, not what they claim</div>
          <ul className="list">
            {boot.cohorts.map(c => (
              <li key={c.idx}>
                <button className="click" onClick={() => go('cohort=' + c.idx)}>
                  <span className="dot" style={{ background: cohortColor(c.idx) }} />{c.label}
                </button>
                <span className="num">{c.size}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h3>Most-subscribed events</h3>
          <div className="sub">RSVP volume — open one for its cohort mix and enjoyment proxy</div>
          <ul className="list">
            {top.map(c => (
              <li key={c.ext_id}>
                <button className="click" onClick={() => go('class=' + c.ext_id)}>{c.title}</button>
                <span className="num">{c.n}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <p className="footnote">⚠ {m.note}</p>
    </>
  )
}

function PersonView({ alias, boot }: { alias: string; boot: Bootstrap }) {
  const [p, setP] = useState<PersonRead | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => { setP(null); fetchPerson(alias).then(setP).catch(e => setErr(String(e))) }, [alias])
  if (err) return <div className="err">{err}</div>
  if (!p) return <Spinner label="computing read in postgres…" />
  if (!p.alias) return <div className="err">no such person</div>
  const titleToId = (t: string) => boot.classes.find(c => c.title === t)?.ext_id
  return (
    <div className="card">
      <div className="read-head">
        <h2>{p.alias}</h2>
        {p.cohort != null
          ? <span className="badge" style={{ borderColor: cohortColor(p.cohort), color: cohortColor(p.cohort) }}>
              <span className="dot" style={{ background: cohortColor(p.cohort) }} />{p.cohort_label}</span>
          : <span className="badge">no stable cohort · communal-only</span>}
        <span className="badge">{p.n_classes} events</span>
        <span className="badge">pseudonym — names never leave the operator's machine</span>
      </div>
      <Chips items={p.signature.tags} />
      <div className="grid2" style={{ marginTop: 20 }}>
        <div className="block">
          <h4>Predicted next events</h4>
          <ul className="list">
            {p.predicted_classes.length ? p.predicted_classes.map(([t, n]) => (
              <li key={t}>
                <button className="click" onClick={() => { const id = titleToId(t); if (id) go('class=' + id) }}>{t}</button>
                <span className="num pred-num">{n} peers</span>
              </li>
            )) : <li className="empty">needs a stable cohort</li>}
          </ul>
          <p className="footnote">events their cohort attends that they haven't — ranked by cohort-mates going</p>
          <h4 style={{ marginTop: 18 }}>Strongest co-attendees</h4>
          <div className="tag-people">
            {p.co_attendees.map(([n]) => (
              <button key={n} className="person-tag" onClick={() => go('person=' + n)}>{n}</button>
            ))}
          </div>
          <h4 style={{ marginTop: 18 }}>Rose Glass essence</h4>
          <button className="chip k click" onClick={() => go('essence=' + p.alias)}>read this person through the lenses →</button>
        </div>
        <div className="block">
          <h4>Signature</h4>
          <Chips items={p.signature.tracks} />
          <div style={{ height: 8 }} />
          <Chips items={p.signature.hosts} />
          <h4 style={{ marginTop: 18 }}>Price their attention</h4>
          <button className="chip k click" onClick={() => go('market=' + p.alias)}>open the attention market →</button>
        </div>
      </div>
      <div className="block" style={{ marginTop: 18 }}>
        <h4>Events attended ({p.classes.length}{p.n_classes > p.classes.length ? ` of ${p.n_classes}` : ''})</h4>
        <div className="chips">
          {p.classes.map(c => (
            <button key={c.ext_id} className="chip click" onClick={() => go('class=' + c.ext_id)}>{c.title}</button>
          ))}
        </div>
      </div>
    </div>
  )
}

function ClassView({ id, boot }: { id: string; boot: Bootstrap }) {
  const [c, setC] = useState<ClassRead | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => { setC(null); fetchClass(id).then(setC).catch(e => setErr(String(e))) }, [id])
  if (err) return <div className="err">{err}</div>
  if (!c) return <Spinner label="computing read in postgres…" />
  const total = c.cohort_mix.reduce((a, [, n]) => a + n, 0) || 1
  const gauge = (lab: string, v: number | null) => (
    <div className="gauge">
      <div className="lab"><span>{lab}</span><b>{v == null ? 'n/a' : Math.round(v * 100) + '%'}</b></div>
      <div className="track"><div className="fill" style={{ width: (v || 0) * 100 + '%' }} /></div>
    </div>
  )
  return (
    <div className="card">
      <div className="read-head">
        <h2>{c.title}</h2>
        <span className="badge">{c.attendee_count} RSVPs</span>
        {c.track && <span className="badge">{c.track}</span>}
        {c.host && <span className="badge">host · {c.host}</span>}
        {c.upcoming && <span className="badge" style={{ color: 'var(--teal)', borderColor: 'rgba(79,216,196,0.4)' }}>upcoming · {fmtTime(c.start)}</span>}
      </div>
      <div className="chips">{c.tags.map(t => <span key={t} className="chip k">{t}</span>)}</div>
      <div className="grid2" style={{ marginTop: 20 }}>
        <div className="block">
          <h4>Cohort mix — who shows up</h4>
          <div className="mixbar">
            {c.cohort_mix.map(([ci, n]) => (
              <i key={ci} style={{ width: (n / total) * 100 + '%', background: cohortColor(ci) }} />
            ))}
          </div>
          <div className="legend">
            {c.cohort_mix.length ? c.cohort_mix.map(([ci, n]) => (
              <button key={ci} onClick={() => go('cohort=' + ci)}>
                <span className="dot" style={{ background: cohortColor(ci) }} />
                {boot.cohorts[ci]?.label ?? 'cohort ' + ci} · {n}
              </button>
            )) : <span className="empty" style={{ padding: 0 }}>no clustered attendees</span>}
          </div>
          <h4 style={{ marginTop: 20 }}>Enjoyment proxy <span style={{ textTransform: 'none', letterSpacing: 0 }}>(reattendance)</span></h4>
          {gauge('came back to this host elsewhere', c.enjoyment.host_return)}
          {gauge('came back to this track elsewhere', c.enjoyment.track_return)}
          <p className="footnote">the etiquette-proof signal: did the room return to the same host / track — not a survey, not applause</p>
        </div>
        <div className="block">
          <h4>RSVP'd ({c.attendees.length} shown)</h4>
          <div className="tag-people">
            {c.attendees.map(a => (
              <button key={a} className="person-tag" onClick={() => go('person=' + a)}>{a}</button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function CohortView({ idx, boot }: { idx: number; boot: Bootstrap }) {
  const c = boot.cohorts.find(x => x.idx === idx)
  if (!c) return <div className="err">no such cohort</div>
  const titleToId = (t: string) => boot.classes.find(x => x.title === t)?.ext_id
  return (
    <div className="card">
      <div className="read-head">
        <h2><span className="dot" style={{ background: cohortColor(idx), width: 15, height: 15 }} />{c.label}</h2>
        <span className="badge">{c.size} people</span>
        <span className="badge">cohort {idx}</span>
      </div>
      <div className="grid2" style={{ marginTop: 16 }}>
        <div className="block">
          <h4>What binds them</h4>
          <Chips items={c.tags} />
          <div style={{ height: 8 }} />
          <Chips items={c.tracks} />
          <div style={{ height: 8 }} />
          <Chips items={c.hosts} />
        </div>
        <div className="block">
          <h4>Signature events</h4>
          <div className="chips">
            {c.signature_classes.map(t => (
              <button key={t} className="chip click" onClick={() => { const id = titleToId(t); if (id) go('class=' + id) }}>{t}</button>
            ))}
          </div>
          <h4 style={{ marginTop: 18 }}>Core members</h4>
          <div className="tag-people">
            {c.members.map(a => <button key={a} className="person-tag" onClick={() => go('person=' + a)}>{a}</button>)}
          </div>
        </div>
      </div>
    </div>
  )
}

function MarketView({ alias, boot }: { alias?: string; boot: Bootstrap }) {
  const clustered = useMemo(() => boot.people.filter(p => p.cohort != null), [boot])
  const self = alias && clustered.some(p => p.alias === alias) ? alias : clustered[0]?.alias
  const [m, setM] = useState<MarketRead | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    if (!self) return
    setM(null)
    fetchMarket(self).then(setM).catch(e => setErr(String(e)))
  }, [self])
  if (err) return <div className="err">{err}</div>
  const head = (
    <div className="card">
      <div className="mkt-head">
        <h2>The Attention Market</h2>
        <span style={{ color: 'var(--faint)', fontSize: 12 }}>clearing for</span>
        <select className="selfpick" value={self} onChange={e => go('market=' + e.target.value)}>
          {clustered.map(p => <option key={p.alias} value={p.alias}>{p.alias} · {boot.cohorts[p.cohort!]?.label.split(' · ')[0]}</option>)}
        </select>
      </div>
      <p className="lede" style={{ fontSize: 13.5, color: 'var(--dim)', margin: 0 }}>
        Attention is finite, so it's tradeable. Each future time-slot is a market: competing events <b>bid</b> with
        their predicted enjoyment for this person — priced from their cohort's revealed affinity, cleared in Postgres,
        settled later on reattendance. The spread between the top two bids is the <b>opportunity cost</b> of choosing wrong.
      </p>
    </div>
  )
  if (!m) return <>{head}<Spinner label="clearing the market server-side…" /></>
  const schedule = m.slots.map(s => ({ t: s.start, w: s.events[0] })).slice(0, 12)
  return (
    <>
      {head}
      <div className="card">
        <h3>Optimal attention schedule</h3>
        <div className="sub">{m.slots.length} contested slots · cohort: {m.cohort_label}</div>
        <ul className="list">
          {schedule.map(x => (
            <li key={x.t}>
              <button className="click" style={{ fontWeight: 600 }} onClick={() => go('class=' + x.w.ext_id)}>{x.w.title}</button>
              <span className="num">{fmtTime(x.t)} · {x.w.pct}</span>
            </li>
          ))}
          {!schedule.length && <li className="empty">no contested upcoming slots</li>}
        </ul>
      </div>
      {m.slots.map(s => (
        <div className="slot" key={s.start}>
          <div className="slot-time">{fmtTime(s.start)}</div>
          {s.events.map((e, i) => (
            <div className={'bidrow' + (i === 0 ? ' win' : '')} key={e.ext_id}>
              <button className="nm click" onClick={() => go('class=' + e.ext_id)}>
                {e.title}{i === 0 && <span className="wintag">ATTENTION</span>}
                <span className="mut"> · {e.track || e.host || ''}</span>
              </button>
              <span className="track2"><span className="fill2" style={{ width: e.pct + '%' }} /></span>
              <span className="pct">{e.pct}</span>
            </div>
          ))}
          <div className="oc">cost of skipping the top pick here: <b>{s.oc}</b> enjoyment-pts</div>
        </div>
      ))}
    </>
  )
}

/* ---------- shell ---------- */

export default function App() {
  const [boot, setBoot] = useState<Bootstrap | null>(null)
  const [err, setErr] = useState('')
  const [route, setRoute] = useState<Route>(parseHash())
  const [q, setQ] = useState('')
  const searchRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchBootstrap().then(setBoot).catch(e => setErr(String(e)))
    const onHash = () => { setRoute(parseHash()); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) setQ('')
    }
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [])

  const results = useMemo(() => {
    if (!boot || !q.trim()) return []
    const s = q.trim().toLowerCase()
    const pp = boot.people.filter(p => p.alias.includes(s)).slice(0, 6)
      .map(p => ({ t: 'person' as const, label: p.alias, sub: p.n + ' events', go: 'person=' + p.alias }))
    const cc = boot.classes.filter(c => c.title?.toLowerCase().includes(s)).slice(0, 6)
      .map(c => ({ t: 'class' as const, label: c.title, sub: c.n + ' RSVPs', go: 'class=' + c.ext_id }))
    return [...pp, ...cc].slice(0, 10)
  }, [boot, q])

  if (err) return <div className="err" style={{ padding: 60 }}>{err}</div>

  return (
    <div className="app">
      <aside className="side">
        <div className="brand" onClick={() => go('')}>
          <h1>cerata</h1><span className="ver">SUPABASE EDITION</span>
        </div>
        <div className="tagline">revealed-preference reads · Edge Esmeralda 2026</div>
        <div className="live">
          <span className="pulse" />LIVE · POSTGRES{lastLatency ? ` · ${lastLatency}MS` : ''}
        </div>
        <div className="search-wrap" ref={searchRef}>
          <input className="search" placeholder="Load a person or event…" value={q}
            onChange={e => setQ(e.target.value)} />
          {results.length > 0 && (
            <div className="results">
              {results.map(r => (
                <button key={r.go} className="r-item" onClick={() => { go(r.go); setQ('') }}>
                  <span className={'pill ' + r.t}>{r.t}</span><span>{r.label}</span>
                  <span className="sub">{r.sub}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="tabs">
          <button className={'tab' + (['overview', 'person', 'class', 'cohort'].includes(route.v) ? ' active' : '')} onClick={() => go('')}>Reads</button>
          <button className={'tab' + (route.v === 'market' ? ' active' : '')} onClick={() => go('market')}>Market</button>
          <button className={'tab' + (['essences', 'essence'].includes(route.v) ? ' active' : '')} onClick={() => go('essences')}>Essence</button>
        </div>
        <div className="sec-title">Cohorts</div>
        {boot?.cohorts.map(c => (
          <button key={c.idx} className="cohort-chip" onClick={() => go('cohort=' + c.idx)}>
            <b><span className="dot" style={{ background: cohortColor(c.idx) }} />{c.label}</b>
            <div className="meta">{c.size} people · {(c.tracks[0] || ['—'])[0]}</div>
          </button>
        ))}
        <div className="caveat">
          ⚠ RSVP-based (check-in ~0.3%). Predicts who <b>signs up</b>; enjoyment = reattendance, not applause.
          People are pseudonymous — real names never reach this database.
        </div>
        <div className="stack">
          <b>stack</b> · supabase postgres 17<br />
          facts → <b>cerata</b> schema (RLS-locked)<br />
          analytics → SQL views · market → RPC<br />
          ingest → edge function · names → never
        </div>
      </aside>
      <main className="main">
        {!boot ? <Spinner label="booting from supabase…" /> : (
          <>
            {route.v === 'overview' && <Overview boot={boot} />}
            {route.v === 'person' && <><div className="crumb"><button onClick={() => go('')}>⌂ reads</button> / person</div><PersonView alias={route.alias} boot={boot} /></>}
            {route.v === 'class' && <><div className="crumb"><button onClick={() => go('')}>⌂ reads</button> / event</div><ClassView id={route.id} boot={boot} /></>}
            {route.v === 'cohort' && <><div className="crumb"><button onClick={() => go('')}>⌂ reads</button> / cohort</div><CohortView idx={route.idx} boot={boot} /></>}
            {route.v === 'market' && <MarketView alias={route.alias} boot={boot} />}
            {route.v === 'essences' && <EssenceWall />}
            {route.v === 'essence' && <EssenceView alias={route.alias} />}
          </>
        )}
      </main>
    </div>
  )
}
