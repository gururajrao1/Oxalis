"""Ugly pass 13: network structure of e_coli_core (metabolite degrees).

Currency classes (reasoned, documented):
  bookkeeping: protons + water (stoichiometric balancing, every redox/hydrolysis step)
  carrier: energy (atp/adp/amp, pi/ppi) + redox (nad(h), nadp(h)) + acyl (coa)
           shuttles reused across unrelated pathways
  pathway: everything else (candidate real hubs)
"""
import statistics

import cobra
import pandas as pd

BOOK = {"h", "h2o"}
CARRIER = {"atp", "adp", "amp", "pi", "ppi", "nad", "nadh", "nadp", "nadph", "coa"}


def base(met_id):
    return met_id.rsplit("_", 1)[0]


def cls(met_id):
    b = base(met_id)
    if b in BOOK:
        return "bookkeeping"
    if b in CARRIER:
        return "carrier"
    return "pathway"


m = cobra.io.load_model("textbook")
rows = [{"met": met.id, "formula": met.formula or "", "degree": len(met.reactions),
         "class": cls(met.id)} for met in m.metabolites]
df = pd.DataFrame(rows).sort_values("degree", ascending=False).reset_index(drop=True)
df.to_csv("degrees.csv", index=False)
print("--- top 20 (with currency) ---")
print(df.head(20).to_string(index=False))
deg = df["degree"].tolist()
print(f"n={len(deg)} median={statistics.median(deg):.1f} mean={statistics.mean(deg):.2f}")
d2 = df.query("`class`=='pathway'")["degree"].tolist()
print(f"without currency: n={len(d2)} median={statistics.median(d2):.1f} "
      f"mean={statistics.mean(d2):.2f}")
print("--- top 15 pathway-only ---")
print(df.query("`class`=='pathway'").head(15).to_string(index=False))
