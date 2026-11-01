"""Ugly pass 12: FBA vs linear-MOMA knockout predictions (core, glucose -10).

FBA re-optimizes the mutant to its new global optimum (adapted strain).
MOMA stays closest to the wild-type flux state (fresh knockout).
They disagree exactly where rewiring is expensive: showcase + quantify.
"""
import cobra
from cobra.flux_analysis import moma

SYMS = ["pgi", "pfkA", "tpiA", "gapA", "pgk", "eno", "ppc", "zwf", "gnd",
        "pta", "ackA", "pflB", "adhE", "ldhA"]


def compare(model_name="core"):
    m0 = (cobra.io.load_model("textbook") if model_name == "core"
          else cobra.io.load_json_model("iML1515.json"))
    sym2id = {g.name: g.id for g in m0.genes if g.name}
    bio = next(r.id for r in m0.reactions if "biomass" in r.id.lower())
    rows = []
    for cond, o2 in [("aerobic", -1000.0), ("anaerobic", 0.0)]:
        wt = m0.copy()
        wt.reactions.EX_glc__D_e.lower_bound = -10.0
        wt.reactions.EX_o2_e.lower_bound = o2
        wt_sol = wt.optimize()
        wt_g = float(wt_sol.objective_value)
        for sym in SYMS:
            if sym not in sym2id:
                continue
            gid = sym2id[sym]
            ko = m0.copy()
            ko.reactions.EX_glc__D_e.lower_bound = -10.0
            ko.reactions.EX_o2_e.lower_bound = o2
            ko.genes.get_by_id(gid).knock_out()
            ksol = ko.optimize()
            fba_g = float(ksol.objective_value) if ksol.status == "optimal" else 0.0
            try:
                msol = moma(ko, solution=wt_sol, linear=True)
                moma_g = float(msol.fluxes[bio]) if msol.status == "optimal" else 0.0
            except Exception as e:
                moma_g = float("nan")
                print(f"  MOMA failed {gid}/{cond}: {e}")
            rows.append({"gene": gid, "sym": sym, "cond": cond,
                         "wt": wt_g, "fba": fba_g, "moma": moma_g})
            flag = "  <-- DISAGREE" if (fba_g > 0.05 * wt_g) != (moma_g > 0.05 * wt_g) else ""
            print(f"{sym:6s} {cond:9s} wt={wt_g:.3f} fba={fba_g:.3f} moma={moma_g:.3f}{flag}")
    return rows


if __name__ == "__main__":
    import pandas as pd
    pd.DataFrame(compare("core")).to_csv("moma_compare.csv", index=False)
    print("saved moma_compare.csv")
