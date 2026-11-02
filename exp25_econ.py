"""Exp 25: enzyme-constrained E. coli (eciML1515, GECKO) vs our residuals.

Why: plain FBA overpredicts growth (mu +38% in the batch fit, +8.5% on V&P)
and its overflow is pure stoichiometry. eciML1515 adds enzyme-capacity
constraints (protein pool), which is the literature fix for both
(SysBioChalmers ecModels, GECKO).
Load note: cobra's default SBML import applies F_REPLACE, which unescapes
GECKO's `__32__` (ascii-32 = space) into real spaces, producing reaction
ids optlang rejects ("protein pseudoreaction"). Load with f_replace=None
(raw R_/M_/G_ ids) instead.
Comparisons (same conditions as exps 1/5/6):
  - glucose -10 aerobic / anaerobic: mu + fermentation products
  - V&P measured uptakes: q_glc=10.5/o2cap=15 aerobic, q_glc=18.5 anaerobic
"""
import warnings

import cobra
import pandas as pd

warnings.filterwarnings("ignore")

# GECKO splits every reversible into forward (secretion, 0..1000) + _REV
# twin (uptake, 0..1000). Uptake is capped via the _REV upper bound;
# secretions are read (positive) off the forward reactions.
EX = {"glc": "R_EX_glc__D_e", "o2": "R_EX_o2_e", "ac": "R_EX_ac_e",
      "etoh": "R_EX_etoh_e", "for": "R_EX_for_e", "lac": "R_EX_lac__D_e",
      "succ": "R_EX_succ_e", "co2": "R_EX_co2_e"}
REV = {k: v + "_REV" for k, v in EX.items()}
BIO = "R_BIOMASS_Ec_iML1515_core_75p37M"


_EC = None
_CAP = None

# API-first: the 10 MB ecModel streams from SysBioChalmers into the OS temp
# dir on first use (evict anytime); a repo-local copy is used if present.
EC_URL = ("https://raw.githubusercontent.com/SysBioChalmers/ecModels/main/"
          "eciML1515/model/eciML1515.xml")


def ec_xml_path():
    import tempfile
    import urllib.request
    from pathlib import Path
    local = Path(__file__).parent / "eciML1515.xml"
    if local.exists():
        return str(local)
    dest = Path(tempfile.gettempdir()) / "oxalis_cache" / "eciML1515.xml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        urllib.request.urlretrieve(EC_URL, dest)
    return str(dest)


def load_ec():
    """Load once per process (a fresh 10 MB SBML parse is ~2 min)."""
    global _EC
    if _EC is None:
        _EC = cobra.io.read_sbml_model(ec_xml_path(), f_replace=None)
        ids = {rx.id for rx in _EC.reactions}
        for r in list(EX.values()) + list(REV.values()):
            assert r in ids, f"missing {r}"
    return _EC


def get_cap(m):
    """Single protein-cap constraint object, reused across sims (no copies:
    each sim only resets bounds + the cap ub on the shared model)."""
    global _CAP
    if _CAP is None:
        from sympy import Add
        I = m.solver.interface
        terms = enzyme_terms(m)
        # One Add call, not a Python sum loop: incremental `expr + term`
        # re-canonicalizes the whole sympy tree each step (O(n^2), hangs).
        expr = Add(*[r.flux_expression * w for r, w in terms])
        _CAP = I.Constraint(expr, ub=P_TOTAL, name="protein_cap")
        m.solver.add(_CAP)
        print(f"protein cap over {len(terms)} arms", flush=True)
    return _CAP


# Minimal mineral medium (uptake twins left open; everything else closed).
MEDIUM = ["glc", "o2", "co2", "h", "h2o", "nh4", "pi", "so4", "ca2", "cl",
          "cobalt2", "cu2", "fe2", "fe3", "k", "mg2", "mn2", "mobd", "na1",
          "ni2", "zn2"]

# Uniform-MW protein cap (sMOMENT-lite): sum over enzyme-usage arms of
# flux * coeff * MW <= P_total. Uniform MW and P_total are assumptions
# (sensitivity-tested below); per-enzyme MW/abundance needs proteomics.
MW_G_PER_MMOL = 40.0  # 40 kDa average bacterial protein
P_TOTAL = 0.5  # g enzyme / gDW cap


def enzyme_terms(m):
    """(reaction, mass-per-flux) for arms drawing enzyme pseudo-mets."""
    terms = []
    for r in m.reactions:
        if r.id.startswith("R_prot_") and "exchange" in r.id:
            continue
        for met, coeff in r.metabolites.items():
            if met.id.startswith("M_prot_") and coeff < 0:
                terms.append((r, -coeff * MW_G_PER_MMOL))
                break
    return terms


def medium_id(key):
    return f"R_EX_{key}_e_REV"


def sim(glc, o2cap, p_total=None):
    m = load_ec()
    # Batch setup: close every medium uptake except the mineral list (the
    # model ships with all 100+ uptakes open; only the carbon source is free).
    ids = {r.id for r in m.reactions}
    for r in m.reactions:
        if r.id.startswith("R_EX_") and r.id.endswith("_REV"):
            r.upper_bound = 0.0
    for key in MEDIUM:
        rid = medium_id(key)
        if rid in ids:
            m.reactions.get_by_id(rid).upper_bound = 1000.0
    m.reactions.get_by_id(REV["glc"]).upper_bound = glc
    m.reactions.get_by_id(REV["o2"]).upper_bound = o2cap
    if p_total:
        get_cap(m).ub = p_total
    elif _CAP is not None:
        _CAP.ub = 1000.0  # cap object exists from an earlier sim: relax it
    s = m.optimize()
    f = s.fluxes if s.status == "optimal" else {}
    g = lambda r: float(f.get(EX[r], 0.0)) if s.status == "optimal" else 0.0
    # Objective is fwd - rev twin; read growth off the forward flux.
    mu = float(f.get(BIO, 0.0)) if s.status == "optimal" else 0.0
    return {"glc": glc, "o2cap": o2cap, "status": s.status, "growth": mu,
            "ac": g("ac"), "etoh": g("etoh"), "for": g("for"),
            "lac": g("lac"), "succ": g("succ"), "co2": g("co2")}


if __name__ == "__main__":
    rows = []
    # uncapped: validates the import (must reproduce plain iML1515 exactly)
    r = sim(10.0, 1000.0)
    r["cond"] = "aerobic glc-10 uncapped"
    rows.append(r)
    print(f"{r['cond']}: mu={r['growth']:.4f}")
    # protein-cap sensitivity: P<=0.3 barely bound (mu 0.864 vs 0.877),
    # so probe the tight regime + VP/anaerobic at two of those points.
    for p in [0.05, 0.1, 0.15, 0.2]:
        for glc, o2cap, tag in [(10.0, 1000.0, "aerobic glc-10")] + (
                [(10.5, 15.0, "aerobic VP"), (18.5, 0.0, "anaerobic q18.5")]
                if p in (0.1, 0.15) else []):
            r = sim(glc, o2cap, p_total=p)
            r["cond"] = f"{tag} P<={p}"
            rows.append(r)
            print(f"{r['cond']}: mu={r['growth']:.4f} ac={r['ac']:.2f} "
                  f"etoh={r['etoh']:.2f} for={r['for']:.2f} "
                  f"lac={r['lac']:.2f}")
    pd.DataFrame(rows).to_csv("ec_compare.csv", index=False)
    print("saved ec_compare.csv")
