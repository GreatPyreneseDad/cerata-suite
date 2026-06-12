import { useEffect, useState } from 'react'
import {
  DIMS, DIM_GLYPH, DIM_LABEL, Essence, EssenceCard, LensRead, Signal,
  fetchEssence, fetchEssences, lensVec, lensFamilyColor,
} from './lib/api'

const go = (h: string) => { location.hash = h }

/* The interference polygon — Hand 1. Each lens is a translucent pentagon over
   the five Rose Glass dimensions; where they fail to overlap is λ, the moiré.
   No synthesis: the lenses are never merged into one shape. */
export function InterferencePolygon({ reads, size = 230 }: { reads: LensRead[]; size?: number }) {
  const cx = size / 2, cy = size / 2, R = size * 0.36
  const pts = (vec: Record<string, number>) =>
    DIMS.map((d, i) => {
      const a = (i / DIMS.length) * Math.PI * 2 - Math.PI / 2
      const r = R * Math.max(0.04, vec[d])
      return [cx + Math.cos(a) * r, cy + Math.sin(a) * r]
    })
  const poly = (p: number[][]) => p.map(xy => xy.join(',')).join(' ')
  const axis = DIMS.map((d, i) => {
    const a = (i / DIMS.length) * Math.PI * 2 - Math.PI / 2
    return { d, x: cx + Math.cos(a) * R, y: cy + Math.sin(a) * R,
      lx: cx + Math.cos(a) * (R + 16), ly: cy + Math.sin(a) * (R + 16) }
  })
  return (
    <svg viewBox={`0 0 ${size} ${size}`} style={{ width: '100%', maxWidth: size, overflow: 'visible' }}>
      {[0.25, 0.5, 0.75, 1].map(g => (
        <polygon key={g} points={poly(DIMS.map((_, i) => {
          const a = (i / DIMS.length) * Math.PI * 2 - Math.PI / 2
          return [cx + Math.cos(a) * R * g, cy + Math.sin(a) * R * g]
        }))} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={1} />
      ))}
      {axis.map(a => <line key={a.d} x1={cx} y1={cy} x2={a.x} y2={a.y} stroke="rgba(255,255,255,0.07)" />)}
      {reads.map((r, i) => {
        const c = lensFamilyColor(r.family)
        return (
          <polygon key={i} points={poly(pts(lensVec(r)))}
            fill={c} fillOpacity={0.12} stroke={c} strokeWidth={1.6} strokeOpacity={0.85}
            style={{ mixBlendMode: 'screen' }} />
        )
      })}
      {axis.map(a => (
        <text key={a.d} x={a.lx} y={a.ly} textAnchor="middle" dominantBaseline="middle"
          fill="#9aa3b8" fontSize={13} fontFamily="Instrument Serif, serif">{DIM_GLYPH[a.d]}</text>
      ))}
    </svg>
  )
}

/* λ bars — the moiré gap, σ² per dimension. The instrument's silence is the
   point: low bars = lenses agree, tall bars = they diverge. */
export function LambdaBars({ lambda, threshold = 0.02 }: { lambda: Record<string, number>; threshold?: number }) {
  const max = Math.max(threshold * 2, ...DIMS.map(d => lambda[d] || 0))
  return (
    <div>
      {DIMS.map(d => {
        const v = lambda[d] || 0
        const over = v >= threshold
        return (
          <div key={d} className="lam-row">
            <span className="lam-glyph">{DIM_GLYPH[d]}</span>
            <span className="lam-track">
              <span className="lam-fill" style={{ width: (v / max) * 100 + '%', background: over ? 'var(--gold)' : 'var(--teal)' }} />
              <span className="lam-thresh" style={{ left: (threshold / max) * 100 + '%' }} />
            </span>
            <span className="lam-val" style={{ color: over ? 'var(--gold)' : 'var(--faint)' }}>{v.toFixed(4)}</span>
          </div>
        )
      })}
    </div>
  )
}

function VeritasPanel({ s }: { s: Signal }) {
  return s.veritas ? (
    <div className="veritas on">
      <b>VERITAS · LENS-INVARIANT</b>
      <span>all lenses agree within σ² &lt; {s.veritas_threshold} on every dimension — the instrument speaks</span>
    </div>
  ) : (
    <div className="veritas off">
      <b>VERITAS · SILENT</b>
      <span>the lenses diverge; the instrument does not declare truth where its perceivers disagree</span>
    </div>
  )
}

function SignalBlock({ s }: { s: Signal }) {
  return (
    <div className="card">
      <div className="sig-head">
        <span className="badge">{s.source}</span>
        <span className="badge">{s.char_count} chars perceived</span>
        <span className="badge">{s.reads.length} lenses</span>
        <span className="badge" style={{ color: 'var(--faint)' }}>raw text never stored</span>
      </div>
      <VeritasPanel s={s} />
      <div className="ess-grid">
        <div className="block" style={{ textAlign: 'center' }}>
          <h4>Interference polygon · Hand 1</h4>
          <InterferencePolygon reads={s.reads} />
          <div className="lens-legend">
            {s.reads.map(r => (
              <span key={r.lens}><span className="dot" style={{ background: lensFamilyColor(r.family) }} />{r.lens}</span>
            ))}
          </div>
          <p className="footnote">two architectures read the same signal; the gap between the pentagons is λ</p>
        </div>
        <div className="block">
          <h4>λ — the moiré gap (σ² between lenses)</h4>
          <LambdaBars lambda={s.lambda} threshold={s.veritas_threshold} />
          <p className="footnote">the teal line is the Veritas threshold; bars past it are where the lenses disagree</p>
        </div>
      </div>
      {s.reads.some(r => r.notes) && (
        <div className="block" style={{ marginTop: 6 }}>
          <h4>What each lens saw</h4>
          <div className="lens-notes">
            {s.reads.filter(r => r.notes).map(r => (
              <div key={r.lens} className="lens-col">
                <div className="lens-col-head" style={{ color: lensFamilyColor(r.family) }}>{r.lens}</div>
                {DIMS.map(d => {
                  const key = d === 'q' ? 'q' : d
                  const note = r.notes?.[key]
                  return note ? (
                    <div key={d} className="lens-note"><b>{DIM_GLYPH[d]}</b> {note}</div>
                  ) : null
                })}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function EssenceView({ alias }: { alias: string }) {
  const [e, setE] = useState<Essence | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => { setE(null); fetchEssence(alias).then(setE).catch(x => setErr(String(x))) }, [alias])
  if (err) return <div className="err">{err}</div>
  if (!e) return <div className="spinner"><div className="ring" /> reading the signal through the lenses…</div>
  return (
    <>
      <div className="crumb"><button onClick={() => go('')}>⌂ reads</button> / <button onClick={() => go('essences')}>essences</button> / {alias}</div>
      <div className="hero" style={{ marginBottom: 18 }}>
        <h2 style={{ fontSize: 34 }}>{alias} <span style={{ color: 'var(--faint)', fontSize: 16 }}>· essence</span></h2>
        <p className="lede" style={{ fontSize: 14 }}>
          Rose Glass read of this person's live language — perceived through independent LLM lenses, kept as the gap
          between them (λ), never synthesized into a verdict. The conversation stayed on the operator's machine; only
          the reading reached the cloud.
        </p>
      </div>
      {e.signals.length ? e.signals.map(s => <SignalBlock key={s.signal_id} s={s} />)
        : <div className="empty">no perceived signals for this person yet</div>}
    </>
  )
}

export function EssenceWall() {
  const [cards, setCards] = useState<EssenceCard[] | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => { fetchEssences().then(setCards).catch(x => setErr(String(x))) }, [])
  if (err) return <div className="err">{err}</div>
  if (!cards) return <div className="spinner"><div className="ring" /> loading perceptions…</div>
  return (
    <>
      <div className="hero" style={{ marginBottom: 22 }}>
        <h2>The <em>essence</em> wall</h2>
        <p className="lede">
          Every person here has been read through the Rose Glass lens panel from their own live language. The polygon is
          their dimensional signature; Veritas fires only where independent architectures agree. {cards.length} perceived
          so far — the live agent adds more each pass.
        </p>
      </div>
      <div className="ess-wall">
        {cards.map(c => (
          <button key={c.alias} className="ess-card" onClick={() => go('essence=' + c.alias)}>
            <div className="ess-card-head">
              <b>{c.alias}</b>
              {c.latest.veritas
                ? <span className="vtag on">VERITAS</span>
                : <span className="vtag off">SILENT</span>}
            </div>
            <InterferencePolygon reads={c.latest.reads} size={150} />
            <div className="ess-card-foot">
              <span>{c.latest.source}</span>
              <span>{c.n_signals} signal{c.n_signals > 1 ? 's' : ''}</span>
            </div>
          </button>
        ))}
      </div>
    </>
  )
}
