import { useEffect, useState } from 'react'
import {
  Cultures, CultureLens, PersonCulture, GROUP_COLOR,
  fetchCultures, fetchPersonCultures,
} from './lib/api'

const go = (h: string) => { location.hash = h }

export function CulturesView() {
  const [c, setC] = useState<Cultures | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => { fetchCultures().then(setC).catch(x => setErr(String(x))) }, [])
  if (err) return <div className="err">{err}</div>
  if (!c) return <div className="spinner"><div className="ring" /> reading the village through every lens…</div>

  const computed = c.lenses.filter(l => !l.needs_language)
  const pending = c.lenses.filter(l => l.needs_language)
  const maxBlind = Math.max(...computed.map(l => l.blind_spot || 0), 0.001)
  const illegPct = Math.round((c.meta.illegible / c.meta.read_people) * 100)

  return (
    <>
      <div className="hero">
        <h2>Whose worldview the village <em>can't see</em></h2>
        <p className="lede">
          Every person is read through {c.meta.computed_lenses} cultural lenses; the lowest-λ lens is their native
          culture. The inverse is the finding: a lens whose profile doesn't match what the village actually programs is
          a <b>structural blind spot</b> — a property of the instrument, never a label on a person.
        </p>
      </div>

      <div className="stat-grid">
        <div className="stat"><b>{c.meta.computed_lenses}</b><span>cultural lenses</span></div>
        <div className="stat"><b>{c.meta.read_people}</b><span>people read</span></div>
        <div className="stat"><b className="accent">{illegPct}%</b><span>illegible · best λ&gt;0.6</span></div>
        <div className="stat"><b>{c.meta.mean_legibility}</b><span>mean legibility λ</span></div>
      </div>

      <div className="card">
        <h3>Lens legibility — the blind-spot spectrum</h3>
        <div className="sub">supply coverage = share of the village's actual programming that serves this culture · longer bar = bigger blind spot</div>
        {computed.map(l => (
          <div key={l.slug} className="lens-bar-row">
            <span className="lens-bar-label" style={{ color: GROUP_COLOR[l.group] }}>{l.label}</span>
            <span className="lens-bar-track">
              <span className="lens-bar-fill" style={{
                width: ((l.blind_spot || 0) / maxBlind) * 100 + '%',
                background: GROUP_COLOR[l.group],
                opacity: 0.35 + 0.5 * ((l.blind_spot || 0) / maxBlind),
              }} />
            </span>
            <span className="lens-bar-meta">
              {l.natives}<span className="mut"> nat</span> · {Math.round((l.supply_coverage || 0) * 100)}%<span className="mut"> sup</span>
            </span>
          </div>
        ))}
        <p className="footnote" style={{ marginTop: 12 }}>
          VC, Agartha, creative, crypto, governance: high blind-spot, near-zero supply — cultures present but unserved.
          Connection, longevity, women's-health: the village's native cultures.
        </p>
      </div>

      {pending.length > 0 && (
        <div className="card">
          <h3>Awaiting the language deep-dive</h3>
          <div className="sub">these register lenses (age axis + shared subcultures) need perceived language, not RSVP behavior — country-of-origin × age is the richer cut</div>
          <div className="chips">
            {pending.map(l => (
              <span key={l.slug} className="chip" style={{ borderColor: GROUP_COLOR[l.group], color: GROUP_COLOR[l.group] }}>{l.label}</span>
            ))}
          </div>
          <p className="footnote" style={{ marginTop: 10 }}>
            Hypothesis under test: the age lenses (boomer first, then non-technical registers) will show the highest
            residual λ of all — the village's lens panel was built by and for millennial-tech culture. Run the perception
            agent on enough language and they light up here.
          </p>
        </div>
      )}
    </>
  )
}

/* Embedded on a person's read: their culture spectrum, native + bicultural. */
export function PersonCultureBlock({ alias }: { alias: string }) {
  const [pc, setPc] = useState<PersonCulture | null>(null)
  useEffect(() => { setPc(null); fetchPersonCultures(alias).then(setPc).catch(() => {}) }, [alias])
  if (!pc || !pc.spectrum?.length) return null
  const top = pc.spectrum.slice(0, 6)
  const illegible = (pc.legibility ?? 0) > 0.6
  return (
    <div className="block" style={{ marginTop: 18 }}>
      <h4>Cultural spectrum · native = lowest λ</h4>
      <div className="cult-spectrum">
        {top.map(s => (
          <div key={s.slug} className={'cult-row' + (s.native ? ' native' : '')}>
            <span className="cult-name" style={{ color: s.native ? GROUP_COLOR[s.group] : 'var(--dim)' }}>
              {s.label}{s.native && <span className="cult-tag">NATIVE</span>}{s.bicultural && <span className="cult-tag bi">bicultural</span>}
            </span>
            <span className="cult-track"><span className="cult-fill" style={{ width: s.fit * 100 + '%', background: GROUP_COLOR[s.group] }} /></span>
            <span className="cult-lam">λ {s.lambda.toFixed(2)}</span>
          </div>
        ))}
      </div>
      <p className="footnote">
        {illegible
          ? `legibility λ ${pc.legibility} — high: no lens natively reads this person, an instrument blind spot.`
          : `native culture: ${pc.native} · legibility λ ${pc.legibility}`}
      </p>
    </div>
  )
}
