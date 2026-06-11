#!/usr/bin/env python3
"""
Interference Polygon — CERATA-SURFACE  (Rose Glass v3 × Index Network)
=====================================================================
We do NOT measure whether a match is "good." We measure the *shape of the
decision surface* the agents are operating — and where that surface bends
away from coherence (interference).

The premise (the mycelium reading):
  Index reconnects humans through a fungal layer of agent intent + negotiation.
  The whole network's fidelity bottlenecks on ONE thing — intent inference.
  Every accept/reject an agent emits is a sample of its decision surface.
  Read enough samples through Rose Glass and the surface's geometry appears:
  a six-dimensional polygon (Ψ ρ q f τ λ) whose distortion IS the interference
  pattern — the literal map of where inference decays and false negatives are born.

Why the LEGAL_ADVERSARIAL lens:
  The Index gate concedes value, then rejects on a token ("strong background,
  but does not explicitly list X"), and produces almost no restoration even
  after 15-19 negotiation turns. That is, behaviorally, an adversarial decision
  environment. v3's LEGAL_ADVERSARIAL calibration encodes exactly that:
  it weights Ψ/ρ attack heaviest and sets κ=0.15 — so temporal depth (deep
  negotiation) barely heals the decay. We read the surface through its own nature.

What this computes, per decision, from the negotiation reasoning text:
  - λΨ  clarity decay      — the decision contradicts its own premise
                             (concedes strength, then rejects: "while X is strong, reject")
  - λρ  density decay      — discards accumulated capability for a missing token
                             ("no evidence of / does not explicitly list <keyword>")
                             >>> the core interference: ρ is *who they are*; the
                             gate trades it for surface frequency. <<<
  - λq  activation decay   — decided mechanically, no engagement with real stakes
  - λf  belonging decay    — surface role/keyword literalism ("this specific role/query")
  - τ   (from turnCount)   — temporal depth the surface was probed to
Then v3's own math:
  λ_total = lambda_decomposition(λΨ,λρ,λq,λf, LEGAL_ADVERSARIAL)
  λ_eff   = tau_attenuated_lambda(λ_total, τ, κ=0.15)   # adversarial: barely attenuates
And aggregates REJECT decisions into the interference polygon, ACCEPT decisions
into the coherence polygon; their gap is the operative decision boundary.

NOTE — honesty about the estimator:
  The per-dimension λ here is a *text-signal first pass* over the reasoning string
  (continuous cousins of cerata-reflect's regex). The rigorous reading runs each
  negotiation through the v3 LLM lens (RoseGlassLLMLens.generate_system_prompt) and
  has the model emit λ/τ/μ directly. This script is the runnable-today version on
  the raw log, and it already resolves the surface clearly. Treat magnitudes as a
  shape, not a measurement.

Usage:
  <list_negotiations JSON, status=all, all pages>  | python3 interference_polygon.py
  ... | python3 interference_polygon.py --json     # raw numbers, no ASCII
Env:
  ROSE_GLASS_V3_PATH  (default /Users/chris/openclaw/rosecorp-products/roseglassv3)
"""
import sys, os, json, re, math

V3 = os.environ.get("ROSE_GLASS_V3_PATH", "/Users/chris/openclaw/rosecorp-products/roseglassv3")
sys.path.insert(0, V3)
try:
    from rose_glass_llm_lens_v2 import (
        tau_attenuated_lambda, lambda_decomposition,
        CALIBRATION_PRESETS, LensCalibration,
    )
    CAL = CALIBRATION_PRESETS[LensCalibration.LEGAL_ADVERSARIAL]
    KAPPA = CAL.kappa
except Exception as e:  # vendored fallback so the instrument runs anywhere
    sys.stderr.write(f"[cerata-surface] v3 not importable ({e}); using vendored adversarial calibration\n")
    class _Cal:  # mirrors v3 LEGAL_ADVERSARIAL weights
        psi_weight, rho_weight, q_weight, f_weight, kappa = 1.4, 1.3, 0.7, 1.0, 0.15
    CAL = _Cal()
    KAPPA = CAL.kappa
    def lambda_decomposition(lp, lr, lq, lf, cal=CAL):
        c = [("Ψ", cal.psi_weight*lp), ("ρ", cal.rho_weight*lr),
             ("q", cal.q_weight*lq), ("f", cal.f_weight*lf)]
        tot = sum(v for _, v in c)
        return {"lambda_total": round(tot, 4),
                "psi_contribution": round(c[0][1], 4), "rho_contribution": round(c[1][1], 4),
                "q_contribution": round(c[2][1], 4), "f_contribution": round(c[3][1], 4),
                "dominant_attack_vector": max(c, key=lambda x: x[1])[0]}
    def tau_attenuated_lambda(lb, tau, kappa=KAPPA):
        return 0.0 if lb <= 0 else lb / (1 + kappa*tau)

TAU_SCALE = 20.0   # turnCount that counts as full temporal depth (τ→1)

# ---- text-signal estimators: reasoning string -> per-dimension decay in [0,1] ----
RHO_MARKERS = [   # discards accumulated capability for a missing token  -> ρ decay
    r"no (explicit )?evidence of", r"does not (explicitly |directly )?(list|mention|provide|indicate)",
    r"lacks?\b", r"without (any )?(explicit|specific)", r"no (direct )?indication",
    r"profile (does not|provides no)", r"not (explicitly )?(list|mention)",
]
RHO_CONCESSION = [  # "while strong / valuable ... reject"  -> the trade is explicit
    r"while .{0,60}(strong|valuable|impressive|capable|exceptional|adept|expertise|relevant)",
    r"despite", r"although", r"though .{0,40}(strong|relevant|capable)",
]
F_MARKERS = [     # surface role/keyword literalism  -> f (belonging) decay
    r"this specific", r"specific (query|role|criterion|project|requirements|technical)",
    r"primary (criterion|discovery query|query)", r"highly specific", r"precise technical",
    r"does not (fit|match|align|satisfy)", r"keyword", r"not the .* host", r"core .* requirement",
]
PSI_MARKERS = [   # internal contradiction (concede-then-reject)  -> Ψ (clarity) decay
    r"while .{0,80}(but|however|reject|does not|cannot)", r"despite .{0,80}(reject|does not|cannot|lack)",
    r"materially (identical|the same)", r"reiterat", r"again reject", r"as (stated|i previously)",
]
Q_ENGAGE = [      # engagement with real stakes lowers q-decay
    r"mutual benefit", r"both parties", r"peer-to-peer", r"valuable to", r"collaborat",
    r"strong (match|fit|connection)", r"directly (align|map)", r"ideal",
]

def _hits(text, pats):
    return sum(1 for p in pats if re.search(p, text, re.I))

def _sat(n, k=1.6):  # saturating 0..1 from a hit count
    return 1.0 - math.exp(-n / k)

def estimate(neg):
    """Return (action, name, turns, {psi,rho,q,f} decays, tau)."""
    text = (neg.get("latestMessagePreview") or "")
    action = neg.get("latestAction")
    turns = neg.get("turnCount", 0) or 0
    tau = min(turns / TAU_SCALE, 1.0)

    if action == "accept":
        # coherent region of the surface: low decay; small residual from any hedging
        hedge = _hits(text, [r"\bwhile\b", r"although", r"not explicitly", r"broad alignment"])
        base = 0.12 + 0.10 * min(hedge, 2)
        eng = _hits(text, Q_ENGAGE)
        return action, _name(neg), turns, {
            "psi": base, "rho": base, "q": max(0.05, base - 0.06 * min(eng, 2)), "f": base,
        }, tau

    if action in ("reject", "rejected_or_stalled"):
        rho = max(_sat(_hits(text, RHO_MARKERS)), 0.45 * _sat(_hits(text, RHO_CONCESSION)))
        # a concession PLUS a token-absence is the sharpest ρ interference: reinforce
        if _hits(text, RHO_CONCESSION) and _hits(text, RHO_MARKERS):
            rho = min(1.0, rho + 0.25)
        f = _sat(_hits(text, F_MARKERS))
        psi = _sat(_hits(text, PSI_MARKERS))
        q = 1.0 - _sat(_hits(text, Q_ENGAGE))   # mechanical reject -> high q-decay
        return action, _name(neg), turns, {"psi": psi, "rho": rho, "q": q, "f": f}, tau

    return action, _name(neg), turns, None, tau

NAME_RE = re.compile(r"\b([A-Z][A-Za-z.\-']+(?:\s+[A-Z][A-Za-z.\-']+){0,2})['’]?s?\b")
def _name(neg):
    t = (neg.get("latestMessagePreview") or "")
    STOP = ("This", "While", "Christopher", "The", "His", "Her", "Their", "I", "Since",
            "Despite", "Although", "Unfortunately", "Given", "As", "Both")
    for pat in (r"for ([A-Z][A-Za-z.\-']+(?:\s+[A-Z][A-Za-z.\-']+){0,2})",
                r"\b([A-Z][A-Za-z.\-']+ [A-Z][A-Za-z.\-']+)['’]s\b",
                r"\b([A-Z][A-Za-z.\-']+ [A-Z][A-Za-z.\-']+) (?:is|does|has|lacks|while)\b",
                r"\bWhile ([A-Z][a-z]+)\b", r"^([A-Z][a-z]+),",
                r"\b([A-Z][a-z]+) (?:is an?|while an?|lacks|does not)\b"):
        m = re.search(pat, t)
        if m and m.group(1).split()[0] not in STOP:
            return m.group(1)
    return (neg.get("counterpartyId") or "?")[:8]


def polygon(rows):
    """Aggregate decisions -> six-axis polygon via v3's lambda_decomposition."""
    if not rows:
        return None
    accP = accR = accQ = accF = accTau = accLam = 0.0
    vectors = {}
    per = []
    for action, name, turns, d, tau in rows:
        dec = lambda_decomposition(d["psi"], d["rho"], d["q"], d["f"], CAL)
        lam_eff = tau_attenuated_lambda(dec["lambda_total"], tau, KAPPA)
        accP += dec["psi_contribution"]; accR += dec["rho_contribution"]
        accQ += dec["q_contribution"];   accF += dec["f_contribution"]
        accTau += tau; accLam += lam_eff
        vectors[dec["dominant_attack_vector"]] = vectors.get(dec["dominant_attack_vector"], 0) + 1
        per.append({"name": name, "turns": turns, "lambda_eff": round(lam_eff, 3),
                    "rho_interference": round(dec["rho_contribution"], 3),
                    "dominant": dec["dominant_attack_vector"]})
    n = len(rows)
    return {
        "n": n,
        "axes": {"Ψ": round(accP/n, 3), "ρ": round(accR/n, 3), "q": round(accQ/n, 3),
                 "f": round(accF/n, 3), "τ": round(accTau/n, 3), "λ_eff": round(accLam/n, 3)},
        "dominant_vector": max(vectors, key=vectors.get) if vectors else None,
        "vector_tally": vectors,
        "per": per,
    }


def hexagon(axes, title):
    """ASCII hexagon with each vertex annotated by its [0,1] axis value."""
    A = axes
    def b(v):  # 8-cell block bar
        f = max(0.0, min(1.0, v)); full = int(round(f*8))
        return "█"*full + "·"*(8-full)
    lines = [
        f"  {title}",
        f"                    Ψ {A['Ψ']:.2f}",
        f"                   /        \\",
        f"        λ {A['λ_eff']:.2f} ·          · ρ {A['ρ']:.2f}",
        f"               |   (gate)    |",
        f"        τ {A['τ']:.2f} ·          · q {A['q']:.2f}",
        f"                   \\        /",
        f"                    f {A['f']:.2f}",
        "",
        f"     Ψ clarity   {b(A['Ψ'])}  {A['Ψ']:.2f}",
        f"     ρ density   {b(A['ρ'])}  {A['ρ']:.2f}   <- accumulated capability",
        f"     q stakes    {b(A['q'])}  {A['q']:.2f}",
        f"     f belonging {b(A['f'])}  {A['f']:.2f}   <- role/keyword literalism",
        f"     τ depth     {b(A['τ'])}  {A['τ']:.2f}   (turns probed)",
        f"     λ decay_eff {b(A['λ_eff'])}  {A['λ_eff']:.2f}",
    ]
    return "\n".join(lines)


def main():
    as_json = "--json" in sys.argv
    data = json.loads(sys.stdin.read())
    negs = (data.get("data", {}) or {}).get("negotiations") or data.get("negotiations") or data
    if isinstance(negs, dict):
        negs = negs.get("negotiations", [])

    # latest decision per counterparty (dedupe continuations)
    latest = {}
    for nrec in negs:
        cid = nrec.get("counterpartyId")
        if cid not in latest or (nrec.get("turnCount", 0) > latest[cid].get("turnCount", 0)):
            latest[cid] = nrec

    rejects, accepts = [], []
    for nrec in latest.values():
        action, name, turns, d, tau = estimate(nrec)
        if d is None:
            continue
        (accepts if action == "accept" else rejects).append((action, name, turns, d, tau))

    interference = polygon(rejects)   # the surface where inference bends away
    coherence = polygon(accepts)      # the surface where it holds

    boundary = None
    if interference and coherence:
        boundary = {k: round(interference["axes"][k] - coherence["axes"][k], 3)
                    for k in interference["axes"]}

    out = {
        "decisions": len(rejects) + len(accepts),
        "rejections": len(rejects), "accepts": len(accepts),
        "lens": "LEGAL_ADVERSARIAL", "kappa": KAPPA,
        "interference_polygon": interference,
        "coherence_polygon": coherence,
        "decision_boundary": boundary,
    }

    if as_json:
        print(json.dumps(out, indent=2)); return

    # ---- human-readable report (the deliverable) ----
    P = []
    P.append("╔══════════════════════════════════════════════════════════════════╗")
    P.append("║  INTERFERENCE POLYGON — the agents' decision surface, in Rose     ║")
    P.append("║  Glass.  Read through the LEGAL_ADVERSARIAL lens (κ=%.2f).         ║" % KAPPA)
    P.append("╚══════════════════════════════════════════════════════════════════╝")
    P.append(f"  {out['decisions']} decisions  ·  {out['rejections']} rejections  ·  {out['accepts']} accepts\n")
    if interference:
        P.append(hexagon(interference["axes"], "── INTERFERENCE SURFACE  (rejections) ──"))
        P.append(f"\n     dominant attack vector across rejections:  {interference['dominant_vector']}"
                 f"   {interference['vector_tally']}")
        P.append("")
    if coherence:
        P.append(hexagon(coherence["axes"], "── COHERENCE SURFACE  (accepts) ──"))
        P.append("")
    if boundary:
        ordered = sorted(((k, v) for k, v in boundary.items() if k != "λ_eff"),
                         key=lambda x: -abs(x[1]))
        P.append("  ── DECISION BOUNDARY  (interference − coherence, per axis) ──")
        for k, v in ordered:
            P.append(f"     {k:<3} {v:+.3f}")
        top = ordered[0]
        P.append(f"\n  → the surface separates accept from reject most along  {top[0]}"
                 f"  (Δ={top[1]:+.3f}).")
    if interference:
        ex = sorted(interference["per"], key=lambda r: -r["rho_interference"])[:6]
        P.append("\n  ── ρ-INTERFERENCE EXTREMES  (capability traded for a token) ──")
        for r in ex:
            P.append(f"     {r['name']:<22} ρ-loss {r['rho_interference']:.2f}"
                     f"  λ_eff {r['lambda_eff']:.2f}  ({r['turns']} turns, hit {r['dominant']})")
    P.append("\n  Reading: where ρ dominates, the gate is discarding *who a person is*")
    P.append("  for a surface token. That bulge is the network's intent-inference limit —")
    P.append("  and the place Rose Glass + cerata can restore what the surface drops.")
    print("\n".join(P))


if __name__ == "__main__":
    main()
