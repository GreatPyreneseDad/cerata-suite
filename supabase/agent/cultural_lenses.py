#!/usr/bin/env python3
"""
cultural_lenses — engineer cultural perspectives, read everyone through them.

A cultural lens is a transparent calibration over observable features (tags,
tracks, host signatures). Each person gets a fit to every lens from their
attendance signature (cosine); native lens = argmin λ (λ = 1 - fit); bicultural
= any lens within EPS of the native. A lens's supply_coverage = how much of the
village's actual programming matches it — low coverage is a structural blind
spot, a property of the instrument/village, never a label on a person.

Strawman scope (this file): content + role lenses computed over RSVP behavior
for all attendees — the natural cohorts in the data. Age + shared-register
lenses are REGISTERED with needs_language=true (the deep dive reads language;
country-of-origin × age is the richer axis noted for later).

Ships {kind:"cultural_lenses"} then {kind:"cultural_reads"} to cerata-ingest.

  python3 cultural_lenses.py            # compute + ship (needs CERATA_ANON_KEY, CERATA_INGEST_TOKEN)
  python3 cultural_lenses.py --dry      # print the legibility ranking, ship nothing
"""
import argparse, hashlib, json, math, os, urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SALT_PATH = os.path.join(HERE, '..', 'ingest', '.salt')
PULL = os.environ.get('CERATA_EDGE_PULL', '/tmp/edge_pull.json')
SUPABASE_URL = os.environ.get('CERATA_SUPABASE_URL', 'https://boupwgkkzexwisctrhdr.supabase.co')
ANON = os.environ.get('CERATA_ANON_KEY', '')
TOKEN = os.environ.get('CERATA_INGEST_TOKEN', '')
EPS = 0.06  # bicultural band: a lens within EPS of the native λ also counts

# ---- the taxonomy. weights are over observable features; t: tag, k: track, h: host-keyword.
# Edited against the real Edge Esmeralda vocabulary. Transparent by design.
LENSES = [
  # builder
  ("ai-agent-builder", "AI-agent builder", "builder", {"t:ai":3,"t:agents":3,"t:vibecoding":3,"t:programming":2,"t:core programming":2,"k:AI week: Intelligence and Autonomy":3,"k:Vibe Code Residency":3}),
  ("crypto-web3", "Crypto / web3 native", "builder", {"t:blockchain & cryptography":3,"t:decentralized technologies":3,"t:protocol research":2,"t:privacy":2,"t:d/acc":2}),
  ("deep-hardtech", "Deep-tech / hardtech", "builder", {"t:hardtech":3,"t:neurotech":3,"t:biotech":2,"k:Neurome":2}),
  ("longevity-biohacker", "Longevity biohacker", "builder", {"t:health & longevity":3,"t:longevity":3,"t:biotech":2,"k:Vital Futures (Health Track)":3}),
  # somatic
  ("somatic-bodywork", "Somatic / bodywork", "somatic", {"t:movement":3,"t:yoga":3,"t:qi gong":3,"t:exercise":2,"t:restore":2,"t:breathwork":2}),
  ("intuitive-healer", "Intuitive / energy healer", "somatic", {"t:wellness":3,"t:wellbeing":2,"t:self care":2,"t:relax":2,"t:sound":2,"t:breath":2}),
  ("womens-health", "Women's-health circle", "somatic", {"k:Women's Health":3,"t:health":2,"t:wellness":1}),
  # esoteric
  ("psychonaut", "Psychonaut / non-normal states", "esoteric", {"k:Psychedelic Futures":3,"t:consciousness":2}),
  ("contemplative", "Contemplative / consciousness", "esoteric", {"k:Contemplative Futures":3,"k:Consciousness Residency":3,"t:philosophy":2,"t:consciousness":2}),
  ("agartha-mystic", "Agartha / mystic", "esoteric", {"k:Agartha":3}),
  # social
  ("connection-facilitator", "Connection-lab facilitator", "social", {"k:Connection / Community Care":3,"t:connection":3,"t:community":2}),
  ("kids-family", "Kids & family / intergenerational", "social", {"t:kids & families":3,"t:food":2}),
  ("governance-civic", "Governance / civic", "social", {"t:governance":3,"t:politics":2,"t:privacy":1}),
  ("regen-climate", "Regen / climate communalist", "social", {"t:climate & sustainability":3,"t:food":2,"t:community":1}),
  # creative
  ("creative-maker", "Creative maker / immersive", "creative", {"t:art & design":3,"t:art":3,"t:creativity":3,"t:storytelling":2,"t:music":2,"k:Production":2}),
  # knowledge
  ("educator", "Educator / philosopher", "knowledge", {"t:education":3,"t:philosophy":3,"t:lunch n learn":2}),
  # role / economic
  ("vc-investor", "VC / investor", "role", {"h:fund":3,"h:capital":3,"h:venture":3,"h:ventures":3,"h:partner":2,"t:core programming":1}),
]
# Registered but language-required — the deep dive. supply_coverage stays null;
# fit comes from perceived language register (and, later, country-of-origin × age).
LANGUAGE_LENSES = [
  ("age-boomer", "Boomer / pre-digital register", "age"),
  ("age-genx", "Gen-X register", "age"),
  ("age-millennial", "Millennial-startup register", "age"),
  ("age-genz", "Gen-Z register", "age"),
  ("edge-insider", "Edge-resident insider register", "shared"),
  ("logistics-coordinator", "Logistics-coordinator register", "shared"),
]


def feat(e):
    out = []
    for t in (e.get("tags") or []):
        out.append("t:" + t)
    if e.get("track_title"):
        out.append("k:" + e["track_title"])
    h = (e.get("host_display_name") or "").lower()
    for tok in h.replace("/", " ").replace(",", " ").split():
        out.append("h:" + tok)
    return out


def cosine(a, b):
    keys = set(a) | set(b)
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    na = math.sqrt(sum(v * v for v in a.values())) or 1e-9
    nb = math.sqrt(sum(v * v for v in b.values())) or 1e-9
    return dot / (na * nb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    salt = open(SALT_PATH).read().strip()
    blob = json.load(open(PULL))
    uniq, rosters = blob["uniq"], blob["rosters"]

    # event feature sets; village-wide supply distribution over features
    ev_feat = {eid: feat(e) for eid, e in uniq.items()}
    supply = defaultdict(float)
    for fs in ev_feat.values():
        for f in fs:
            supply[f] += 1.0
    n_events = len(uniq) or 1

    # supply_coverage per content lens: share of events touching any profile feature,
    # weighted by the lens's own weights (how well the calendar serves this culture)
    def coverage(profile):
        hit = 0.0
        for fs in ev_feat.values():
            score = sum(profile.get(f, 0) for f in fs)
            if score > 0:
                hit += 1.0
        return round(hit / n_events, 4)

    # person attendance signature over features
    person_feat = defaultdict(lambda: defaultdict(float))
    name_pid = {}
    for eid, rows in rosters.items():
        for r in rows:
            pid = r.get("profile_id")
            if not pid:
                continue
            for f in ev_feat.get(eid, []):
                person_feat[pid][f] += 1.0

    salts = lambda pid: hashlib.sha256((salt + pid).encode()).hexdigest()

    lens_rows = []
    for slug, label, grp, profile in LENSES:
        lens_rows.append({"slug": slug, "label": label, "lens_group": grp,
                          "profile": profile, "needs_language": False,
                          "supply_coverage": coverage(profile)})
    for slug, label, grp in LANGUAGE_LENSES:
        lens_rows.append({"slug": slug, "label": label, "lens_group": grp,
                          "profile": {}, "needs_language": True, "supply_coverage": None})

    # per-person fit over the content lenses (RSVP-computable)
    content = [(slug, profile) for slug, _, _, profile in LENSES]
    reads = []
    legib = []
    for pid, fvec in person_feat.items():
        if not fvec:
            continue
        fits = [(slug, cosine(fvec, profile)) for slug, profile in content]
        fits.sort(key=lambda x: -x[1])
        best = fits[0][1]
        native_slug = fits[0][0]
        for slug, fit in fits:
            lam = round(1 - fit, 4)
            reads.append({
                "ext_hash": salts(pid), "lens_slug": slug,
                "fit": round(fit, 4), "lambda": lam,
                "is_native": slug == native_slug,
                "is_bicultural": (best - fit) <= EPS and slug != native_slug,
            })
        legib.append((salts(pid), round(1 - best, 4), native_slug))

    if args.dry:
        # legibility ranking: which lenses are blind spots
        natives = defaultdict(int)
        for _, _, ns in legib:
            natives[ns] += 1
        print("=== lens legibility (blind-spot signal) ===")
        ranked = sorted(lens_rows, key=lambda L: (1 - (L["supply_coverage"] or 0)))
        for L in lens_rows:
            if L["needs_language"]:
                continue
        for slug, label, grp, profile in LENSES:
            cov = coverage(profile)
            nat = natives.get(slug, 0)
            print(f"  {label:32s} supply={cov:.2f}  natives={nat:3d}  blind={'■'*int((1-cov)*20)}")
        illeg = sum(1 for _, b, _ in legib if b > 0.6)
        print(f"\npeople read: {len(legib)}  illegible (best λ>0.6): {illeg}")
        print("age/shared register lenses registered (needs_language): "
              + ", ".join(s for s, _, _ in LANGUAGE_LENSES))
        return

    if not (ANON and TOKEN):
        raise SystemExit("set CERATA_ANON_KEY and CERATA_INGEST_TOKEN to ship")
    url = SUPABASE_URL + "/functions/v1/cerata-ingest"
    def post(body):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
            "Content-Type": "application/json", "Authorization": "Bearer " + ANON,
            "x-ingest-token": TOKEN})
        with urllib.request.urlopen(req, timeout=120) as r:
            print("  ", r.read().decode())

    print("ship lenses:", len(lens_rows))
    post({"kind": "cultural_lenses", "rows": lens_rows})
    print("ship reads:", len(reads))
    for i in range(0, len(reads), 2000):
        post({"kind": "cultural_reads", "rows": reads[i:i + 2000]})
    print(f"done: {len(person_feat)} people × {len(content)} content lenses")


if __name__ == "__main__":
    main()
