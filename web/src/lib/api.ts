import { createClient } from '@supabase/supabase-js'

// Publishable credentials (safe client-side; tables are RLS-locked and the
// only doors are the four pseudonymous cerata_* RPCs).
const URL = import.meta.env.VITE_SUPABASE_URL || 'https://boupwgkkzexwisctrhdr.supabase.co'
const KEY = import.meta.env.VITE_SUPABASE_KEY || 'sb_publishable_dqrIo0XK6N8VhRrrl8UcaA_xIcmoq0_'

export const supabase = createClient(URL, KEY)

export type Pair = [string, number]

export interface Meta {
  people: number; classes: number; upcoming: number; cohorts: number
  modularity: number; checkin_coverage: number; avg_classes: number
  roster_rows: number; note: string
}
export interface Cohort {
  idx: number; label: string; size: number
  tags: Pair[]; tracks: Pair[]; hosts: Pair[]
  signature_classes: string[]; members: string[]
}
export interface PersonIdx { alias: string; cohort: number | null; n: number }
export interface ClassIdx {
  ext_id: string; title: string; track: string | null; host: string | null
  start: string | null; n: number; upcoming: boolean
}
export interface Bootstrap { meta: Meta; cohorts: Cohort[]; people: PersonIdx[]; classes: ClassIdx[] }

export interface PersonRead {
  alias: string; cohort: number | null; cohort_label: string | null; n_classes: number
  classes: { ext_id: string; title: string }[]
  co_attendees: Pair[]; predicted_classes: Pair[]
  signature: { tracks: Pair[]; tags: Pair[]; hosts: Pair[] }
}
export interface ClassRead {
  ext_id: string; title: string; track: string | null; host: string | null
  tags: string[]; start: string | null; end: string | null; upcoming: boolean
  attendee_count: number; cohort_mix: [number, number][]; attendees: string[]
  enjoyment: { host_return: number | null; track_return: number | null }
}
export interface MarketSlot {
  start: string; oc: number
  events: { ext_id: string; title: string; track: string | null; host: string | null; pct: number }[]
}
export interface MarketRead {
  alias: string; cohort: number | null; cohort_label: string | null
  now: string; slots: MarketSlot[]
}

async function rpc<T>(fn: string, args?: Record<string, unknown>): Promise<T> {
  const t0 = performance.now()
  const { data, error } = await supabase.rpc(fn, args)
  if (error) throw new Error(`${fn}: ${error.message}`)
  lastLatency = Math.round(performance.now() - t0)
  return data as T
}

export let lastLatency = 0

export const fetchBootstrap = () => rpc<Bootstrap>('cerata_bootstrap')
export const fetchPerson = (alias: string) => rpc<PersonRead>('cerata_person', { p_alias: alias })
export const fetchClass = (extId: string) => rpc<ClassRead>('cerata_class', { p_ext_id: extId })
export const fetchMarket = (alias: string) => rpc<MarketRead>('cerata_market', { p_alias: alias })

export const COLORS = ['#ff6b85', '#4fd8c4', '#e9c46a', '#9a8cff', '#5ad19a', '#f08a5d', '#7aa2ff', '#d36ad3']
export const cohortColor = (i: number | null | undefined) =>
  i == null ? '#3a4051' : COLORS[i % COLORS.length]

export function fmtTime(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
  } catch { return iso.slice(0, 16) }
}
