"""Ugly pass 9+10: substrate generality + degree-of-reduction sweep on iML1515.

Each substrate at equal CARBON uptake (60 C-mmol/gDW/h), aerobic + anaerobic.
Tests whether the redox story generalizes: yield vs degree of reduction.
"""
import re

import cobra
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

SUBS = {"glucose": "EX_glc__D_e", "xylose": "EX_xyl__D_e", "glycerol": "EX_glyc_e",
        "acetate": "EX_ac_e", "succinate": "EX_succ_e", "pyruvate": "EX_pyr_e"}


def elements_of(met):
    try:
        els = met.elements
        if els:
            return {k: int(v) for k, v in els.items()}
    except Exception:
        pass
    d = {}
    for sym, num in re.findall(r"([A-Z][a-z]?)(\d*)", met.formula or ""):
        d[sym] = d.get(sym, 0) + (int(num) if num else 1)
    return d


def dor_per_c(els):
    c = els.get("C", 0)
    if not c:
        return 0.0
    return (4 * els.get("C", 0) + els.get("H", 0) - 2 * els.get("O", 0)
            - 3 * els.get("N", 0)) / c


def run(sub, ex_id, aerobic):
    m = cobra.io.load_json_model("iML1515.json")
    # close ALL carbon uptakes except the test substrate (secretion stays open)
    for r in m.reactions:
        if r.id.startswith("EX_"):
            mets = list(r.metabolites)
            if len(mets) == 1 and int(elements_of(mets[0]).get("C", 0)) > 0:
                r.lower_bound = 0.0
    met = list(m.reactions.get_by_id(ex_id).metabolites)[0]
    nc = int(elements_of(met).get("C", 0))
    kappa = dor_per_c(elements_of(met))
    m.reactions.get_by_id(ex_id).lower_bound = -60.0 / nc
    m.reactions.EX_o2_e.lower_bound = -1000.0 if aerobic else 0.0
    s = m.optimize()
    mu = float(s.objective_value) if s.status == "optimal" else 0.0
    prods = {}
    if s.status == "optimal":
        for r in m.reactions:
            if r.id.startswith("EX_"):
                fl = float(s.fluxes[r.id])
                mets = list(r.metabolites)
                if fl > 1e-9 and len(mets) == 1:
                    cc = int(elements_of(mets[0]).get("C", 0))
                    if cc > 0 and r.id != ex_id:
                        prods[r.id] = fl * cc / 60.0 * 100  # % of C uptake
    tag = "aerobic" if aerobic else "anaerobic"
    print(f"{sub:9s} {tag:9s} DoR/C={kappa:.2f} mu={mu:.4f} Y/Cmol={mu/60:.5f} "
          f"products=" + str({k: round(v, 1) for k, v in sorted(prods.items())}))
    return {"substrate": sub, "condition": tag, "DoR_C": kappa, "growth": mu,
            "Y_per_Cmol": mu / 60.0, "status": s.status,
            **{f"Cpct_{k}": v for k, v in prods.items()}}


m0 = cobra.io.load_json_model("iML1515.json")
avail = {s: e for s, e in SUBS.items() if e in [r.id for r in m0.reactions]}
print("available:", avail)
rows = []
for sub, ex in avail.items():
    rows.append(run(sub, ex, True))
    rows.append(run(sub, ex, False))
df = pd.DataFrame(rows)
df.to_csv("substrates.csv", index=False)

fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.5))
for cond, mk in [("aerobic", "o"), ("anaerobic", "s")]:
    d = df.query("condition==@cond")
    a1.scatter(d["DoR_C"], d["Y_per_Cmol"], marker=mk, s=60, label=cond)
    for _, r in d.iterrows():
        a1.annotate(r["substrate"], (r["DoR_C"], r["Y_per_Cmol"]), fontsize=8)
a1.set_xlabel("degree of reduction per C")
a1.set_ylabel("yield (gDW / C-mol)")
a1.set_title("yield vs substrate redox state")
a1.legend(fontsize=8); a1.grid(True, alpha=0.3)
ana = df.query("condition=='anaerobic'").set_index("substrate")
cpct = [c for c in ana.columns if c.startswith("Cpct_")]
ana[cpct].rename(columns=lambda c: c.replace("Cpct_EX_", "").replace("_e", "")
                 ).plot(kind="bar", stacked=True, ax=a2)
a2.set_ylabel("% of carbon taken up")
a2.set_title("anaerobic product spectra by substrate")
a2.legend(fontsize=7, bbox_to_anchor=(1.02, 1), loc="upper left")
fig.tight_layout()
fig.savefig("substrates.png", dpi=120)
print("saved substrates.png")
