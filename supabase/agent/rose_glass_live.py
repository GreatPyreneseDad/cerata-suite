#!/usr/bin/env python3
"""
rose_glass_live — the live perception agent.

Pulls fresh language from the network (Telegram via telegram-cli-scripts; geo /
Index Network sources plug in the same way), aggregates it per voice, reads
each voice through the Rose Glass lens panel, and ships ONLY the perception —
per-lens Ψ ρ q f τ, the between-lens variance λ, and the Veritas flag — to the
cerata schema on Supabase. Raw text and real names never leave this machine.

Identity: authors are matched against the EdgeOS pull (first+last name) and
hashed with the same local salt as the attendance ingest, so a Telegram voice
lands on the same pseudonymous person row as their RSVPs. Unmatched voices get
a `tg:`-namespaced hash and their own pseudonym.

Perceivers:
  --perceiver bridge   POST each text to a running rose-glass-horizon bridge
                       (`uvicorn bridge:app --port 8000` in that repo) — the
                       two-lens interferometer (Gemini + Claude).
  --perceiver pending  Write /tmp/cerata_pending_signals.json and stop. An
                       agent session (Claude Code with the rose-glass-horizon
                       MCP) perceives each signal with rose_glass_perceive
                       (four lenses) and ships with --ship-reads.

Ship: POST {kind:"perceptions"} batches to the cerata-ingest edge function.

Examples:
  # one-shot, two-lens bridge
  python3 rose_glass_live.py --chat "Edge Esmeralda 2026" --limit 400 --perceiver bridge

  # live loop, every 20 minutes
  python3 rose_glass_live.py --watch 1200 --perceiver bridge

  # hand the pending file back after MCP perception
  python3 rose_glass_live.py --ship-reads /tmp/cerata_perceived.json
"""
import argparse, hashlib, json, os, re, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SALT_PATH = os.path.join(HERE, '..', 'ingest', '.salt')
TG_DIR = os.environ.get('TELEGRAM_CLI_DIR', os.path.expanduser('~/telegram-cli-scripts'))
SUPABASE_URL = os.environ.get('CERATA_SUPABASE_URL', 'https://boupwgkkzexwisctrhdr.supabase.co')
ANON = os.environ.get('CERATA_ANON_KEY', '')
TOKEN = os.environ.get('CERATA_INGEST_TOKEN', '')
LINE = re.compile(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\]\s+(.+?):\s?(.*)$')

ADJ_CREATURE = None  # lazy import of the ingest alias generator
def _alias(h, taken):
    global ADJ_CREATURE
    if ADJ_CREATURE is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'ing', os.path.join(HERE, '..', 'ingest', 'ingest_edge_pull.py'))
        ing = importlib.util.module_from_spec(spec); spec.loader.exec_module(ing)
        ADJ_CREATURE = ing.alias_for
    return ADJ_CREATURE(h, taken)


def pull_telegram(chat, limit):
    out = subprocess.run(['bun', 'read-messages.ts', chat, '--limit', str(limit)],
                         cwd=TG_DIR, capture_output=True, text=True, timeout=180)
    if out.returncode != 0:
        sys.exit(f'telegram pull failed: {out.stderr[:400]}')
    people, times, cur = {}, {}, None
    for ln in out.stdout.splitlines():
        m = LINE.match(ln)
        if m:
            cur = m.group(2).strip()
            people.setdefault(cur, []).append(m.group(3))
            times.setdefault(cur, []).append(m.group(1))
        elif cur and ln.strip():
            people[cur].append(ln)
    return ({p: ' '.join(t).strip() for p, t in people.items()},
            {p: (min(t), max(t)) for p, t in times.items()})


def identities(authors):
    """author display name -> (ext_hash, alias). EdgeOS-matched voices reuse
    their attendance hash; unmatched get a tg: namespace. All local."""
    salt = open(SALT_PATH).read().strip()
    name_to_pid = {}
    pull = os.environ.get('CERATA_EDGE_PULL', '/tmp/edge_pull.json')
    if os.path.exists(pull):
        blob = json.load(open(pull))
        for rows in blob['rosters'].values():
            for r in rows:
                nm = ((r.get('first_name') or '').strip() + ' ' + (r.get('last_name') or '').strip()).strip()
                if nm and r.get('profile_id'):
                    name_to_pid[nm.lower()] = r['profile_id']
    taken = set()
    out = {}
    for a in authors:
        pid = name_to_pid.get(a.lower())
        h = hashlib.sha256((salt + (pid if pid else 'tg:' + a.lower())).encode()).hexdigest()
        out[a] = (h, _alias(h, taken), bool(pid))
    return out


def perceive_bridge(text, url):
    req = urllib.request.Request(url, data=json.dumps({'signal': text}).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def bridge_to_row(resp):
    """Normalize a rose-glass-horizon /perceive response into reads + λ + veritas.
    The bridge nests each dimension as read.<dim>.{amplitude,description}; errored
    lenses (e.g. Gemini quota) are dropped so only valid perceivers ship."""
    dims = ('psi', 'rho', 'q', 'f', 'tau')
    reads = []
    for lens in resp.get('lenses', []):
        if lens.get('error'):
            continue
        rd = lens.get('read') or {}
        amp = {d: (rd.get(d) or {}).get('amplitude') for d in dims}
        if amp['psi'] is None or all((v in (None, 0)) for v in amp.values()):
            continue
        notes = {d: (rd.get(d) or {}).get('description', '') for d in dims}
        reads.append({
            'lens': lens.get('lens') or lens.get('model') or 'unknown',
            'family': lens.get('family') or ('google' if 'gemini' in str(lens.get('model', '')).lower() else 'anthropic'),
            'psi': amp['psi'], 'rho': amp['rho'],
            'q_raw': lens.get('q_raw', amp['q']), 'q_opt': amp['q'],
            'f': amp['f'], 'tau': amp['tau'], 'notes': notes,
        })
    lam = resp.get('lambda') or resp.get('sigma2') or {}
    ver = resp.get('veritas')
    veritas = bool(ver.get('lens_invariant') or ver.get('invariant')) if isinstance(ver, dict) else bool(ver)
    return reads, lam, veritas


DIM_LABEL = {'psi': 'internal coherence', 'rho': 'earned depth', 'q': 'emotional charge',
             'f': 'belonging', 'tau': 'temporal reach'}
DIM_GLYPH = {'psi': 'Ψ', 'rho': 'ρ', 'q': 'q', 'f': 'f', 'tau': 'τ'}
ARCHETYPE = {
    'f': 'a connector — builds the room more than the argument',
    'psi': 'a coherent voice — holds one throughline',
    'rho': 'a depth-carrier — speaks from integrated experience',
    'q': 'a charged voice — runs on activation',
    'tau': 'a long-arc voice — reaches across time',
}


def infer(reads, lam, veritas):
    """The polygon's reading — Hand 2, offered not declared. Synthesizes the
    shape (dominant + thin dimensions, lens agreement) into one short read."""
    import statistics
    dims = ['psi', 'rho', 'q', 'f', 'tau']
    rkey = {'psi': 'psi', 'rho': 'rho', 'q': 'q_opt', 'f': 'f', 'tau': 'tau'}
    if not reads:
        return None
    mean = {d: statistics.mean(r[rkey[d]] for r in reads) for d in dims}
    top = max(dims, key=lambda d: mean[d])
    low = min(dims, key=lambda d: mean[d])
    arch = ARCHETYPE[top]
    s = (f"{arch} ({DIM_GLYPH[top]} {mean[top]:.2f}), "
         f"thinnest on {DIM_LABEL[low]} ({DIM_GLYPH[low]} {mean[low]:.2f}).")
    if veritas:
        s += " The lenses agree across every dimension (Veritas) — the shape is stable, not an artifact of one reader."
    else:
        dv = max(dims, key=lambda d: lam.get(d, 0))
        s += (f" The lenses diverge most on {DIM_LABEL[dv]} (λ {lam.get(dv, 0):.3f}) — "
              "surface and underside read it differently; that gap is yours to resolve.")
    return s


def ship(rows, batch=10):
    if not (ANON and TOKEN):
        sys.exit('set CERATA_ANON_KEY and CERATA_INGEST_TOKEN to ship')
    url = SUPABASE_URL + '/functions/v1/cerata-ingest'
    for i in range(0, len(rows), batch):
        body = json.dumps({'kind': 'perceptions', 'rows': rows[i:i + batch]}).encode()
        req = urllib.request.Request(url, data=body, headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + ANON,
            'x-ingest-token': TOKEN})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                print('shipped:', r.read().decode())
        except urllib.error.HTTPError as e:
            print(f'ship batch {i} failed {e.code}:', e.read().decode()[:300])


def merge_chats(chats, limit):
    """Pull several chats and merge each author's words across all of them —
    richer behavioral text per voice than any single room gives."""
    texts, times = {}, {}
    for chat in chats:
        try:
            t, w = pull_telegram(chat, limit)
        except SystemExit as e:
            print(f'  skip {chat!r}: {e}'); continue
        for a, txt in t.items():
            texts[a] = (texts.get(a, '') + ' ' + txt).strip()
        for a, (lo, hi) in w.items():
            cur = times.get(a)
            times[a] = (min(lo, cur[0]) if cur else lo, max(hi, cur[1]) if cur else hi)
        print(f'  pulled {chat!r}: {len(t)} voices')
    return texts, times


def run_once(args):
    chats = [c.strip() for c in args.chats.split(';')] if args.chats else [args.chat]
    texts, times = merge_chats(chats, args.limit) if len(chats) > 1 else pull_telegram(chats[0], args.limit)
    ranked = sorted(texts.items(), key=lambda kv: len(kv[1]), reverse=True)
    voices = [(a, t[:args.cap]) for a, t in ranked if len(t) >= args.min_chars][:args.top]
    ids = identities([a for a, _ in voices])
    print(f'voices: {len(voices)} (matched to EdgeOS: {sum(1 for a, _ in voices if ids[a][2])})')

    rows, pending = [], []
    for author, text in voices:
        h, alias, _ = ids[author]
        meta = {
            'ext_hash': h, 'alias': alias, 'source': 'telegram', 'provenance': 'stated',
            'window_start': times[author][0] + ':00Z', 'window_end': times[author][1] + ':00Z',
            'content_hash': hashlib.sha256(text.encode()).hexdigest(), 'char_count': len(text),
        }
        if args.perceiver == 'bridge':
            resp = perceive_bridge(text, args.bridge)
            reads, lam, veritas = bridge_to_row(resp)
            rows.append({**meta, 'reads': reads, 'lambda': lam, 'veritas': veritas,
                         'inference': infer(reads, lam, veritas)})
            print(f'  perceived {alias}: λ={lam} veritas={veritas}')
        else:
            pending.append({**meta, 'signal_text': text})

    if pending:
        out = '/tmp/cerata_pending_signals.json'
        json.dump(pending, open(out, 'w'), ensure_ascii=False, indent=1)
        print(f'wrote {len(pending)} pending signals -> {out}')
        print('perceive each signal_text with rose_glass_perceive, attach reads/lambda/veritas,')
        print('strip signal_text, then: rose_glass_live.py --ship-reads <file>')
        return
    if rows:
        json.dump(rows, open('/tmp/cerata_perceived.json', 'w'))  # save before ship
        print(f'saved {len(rows)} perceived rows -> /tmp/cerata_perceived.json')
        ship(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chat', default='Edge Esmeralda 2026')
    ap.add_argument('--chats', default='', help='semicolon-separated chat names; merges authors across all')
    ap.add_argument('--limit', type=int, default=400)
    ap.add_argument('--top', type=int, default=8)
    ap.add_argument('--min-chars', type=int, default=180)
    ap.add_argument('--cap', type=int, default=1400)
    ap.add_argument('--perceiver', choices=['bridge', 'pending'], default='pending')
    ap.add_argument('--bridge', default='http://localhost:8000/perceive')
    ap.add_argument('--watch', type=int, default=0, help='loop every N seconds')
    ap.add_argument('--ship-reads', help='ship a perceived JSON file (rows with reads attached)')
    args = ap.parse_args()

    if args.ship_reads:
        rows = json.load(open(args.ship_reads))
        for r in rows:
            r.pop('signal_text', None)  # belt and suspenders: text never ships
            if not r.get('inference'):
                r['inference'] = infer(r.get('reads', []), r.get('lambda', {}), r.get('veritas'))
        ship(rows)
        return
    while True:
        run_once(args)
        if not args.watch:
            break
        print(f'sleeping {args.watch}s …')
        time.sleep(args.watch)


if __name__ == '__main__':
    main()
