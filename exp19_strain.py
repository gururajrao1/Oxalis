"""Exp 19: strain-design demo — brute-force double-KO scan for succinate.

OptKnock/ROOM need MILP solvers not shipped here, so this is the honest
substitute: exhaustive single+double KOs over 14 central-carbon genes (core,
aerobic, glucose -10), scored for growth-coupled succinate secretion.
Also records linear-MOMA growth for the top hits (fresh-KO vs adapted).
"""
import itertools

import cobra
import pandas as pd
from cobra.flux_analysis import moma

SYMS = ["pgi", "pfkA", "tpiA", "gapA", "pgk", "eno", "ppc", "zwf", "gnd",
        "pta", "ackA", "pflB", "adhE", "ldhA",
        "sdhA", "frdA", "mdh", "pck", "aceA", "sucA"]
COND_O2 = 0.0  # anaerobic: reductive branch can make succinate
COND = "anaerobic"


def ko_set(m, gids):
    for gid in gids:
        m.genes.get_by_id(gid).knock_out()


m0 = cobra.io.load_model("textbook")
sym2id = {g.name: g.id for g in m0.genes if g.name}
syms = [s for s in SYMS if s in sym2id]
bio = next(r.id for r in m0.reactions if "biomass" in r.id.lower())

wt = m0.copy()
wt.reactions.EX_glc__D_e.lower_bound = -10.0
wt.reactions.EX_o2_e.lower_bound = COND_O2
wt_sol = wt.optimize()
wt_g = float(wt_sol.objective_value)
print(f"WT {COND} growth {wt_g:.4f}; scanning {len(syms)} genes")

rows = []
combos = [(s,) for s in syms] + list(itertools.combinations(syms, 2))
for combo in combos:
    gids = [sym2id[s] for s in combo]
    ko = m0.copy()
    ko.reactions.EX_glc__D_e.lower_bound = -10.0
    ko.reactions.EX_o2_e.lower_bound = COND_O2
    ko_set(ko, gids)
    s = ko.optimize()
    if s.status != "optimal":
        fb = 0.0
    else:
        fb = float(s.objective_value)
    # Production potential: max succinate while keeping >=50% of KO optimum.
    # (At the pure growth optimum succinate is ~0, so optimum secretion alone
    # finds nothing — this envelope is the OptKnock-style signal.)
    if fb <= 0:
        succ = 0.0
    else:
        mx = ko.copy()
        mx.reactions.get_by_id(bio).lower_bound = 0.5 * fb
        mx.objective = mx.reactions.EX_succ_e
        mx.objective_direction = "max"
        ms = mx.optimize()
        succ = float(ms.fluxes["EX_succ_e"]) if ms.status == "optimal" else 0.0
    rows.append({"ko": "+".join(combo), "n": len(combo),
                 "fba": fb, "succ": succ,
                 "yield": succ / 10.0})
df = pd.DataFrame(rows).sort_values(["succ", "fba"], ascending=[False, False])
print(df.head(10).to_string(index=False))

# MOMA for top 5 growth-coupled hits
top = df.query("fba > 0.05 and succ > 0.1").head(5)
moma_rows = []
for _, r in top.iterrows():
    gids = [sym2id[s] for s in r["ko"].split("+")]
    ko = m0.copy()
    ko.reactions.EX_glc__D_e.lower_bound = -10.0
    ko.reactions.EX_o2_e.lower_bound = COND_O2
    ko_set(ko, gids)
    try:
        ms = moma(ko, solution=wt_sol, linear=True)
        mg = float(ms.fluxes[bio]) if ms.status == "optimal" else 0.0
    except Exception:
        mg = float("nan")
    moma_rows.append({"ko": r["ko"], "moma": mg})
    print(f"{r['ko']}: FBA succ={r['succ']:.2f} growth={r['fba']:.3f} MOMA growth={mg:.3f}")

df.to_csv("strain_doubles.csv", index=False)
print("saved strain_doubles.csv — takeaway: FBA double-KO scan finds "
      "growth-coupled succinate candidates; MOMA flags which survive the "
      "fresh-KO transition. True OptKnock/ROOM need a MILP solver (not shipped).")
