"""Ugly pass 14: single-gene deletion screen on the CORE model (teaching version).

Bins: lethal (<1% WT), crippling (1-50%), mild (50-95%), no effect (>95%).
Lethal functions come from the model's own GPR annotation (gene -> reactions).
"""
import cobra
import pandas as pd
from cobra.flux_analysis.deletion import single_gene_deletion


def gid(x):
    return x if isinstance(x, str) else next(iter(x))


m = cobra.io.load_model("textbook")
wt = m.slim_optimize()
print(f"wild type growth: {wt:.4f}")
res = single_gene_deletion(m, processes=1)
res = res.copy()
res["gene"] = res["ids"].apply(gid)
res["frac"] = res["growth"] / wt


def bin(f):
    if f < 0.01:
        return "lethal"
    if f < 0.50:
        return "crippling"
    if f < 0.95:
        return "mild"
    return "none"


res["bin"] = res["frac"].apply(bin)
names = {g.id: (g.name or g.id) for g in m.genes}
res["name"] = res["gene"].map(names)
res[["gene", "name", "growth", "frac", "bin"]].to_csv("core_ko.csv", index=False)
print(res["bin"].value_counts().to_string())
print("--- lethals and what they do (model annotation) ---")
for _, r in res.query("bin=='lethal'").iterrows():
    g = m.genes.get_by_id(r["gene"])
    rxns = sorted({(rx.id, rx.name, rx.subsystem) for rx in g.reactions})
    print(f"{r['gene']} ({r['name']}):")
    for rid, rn, sub in rxns:
        print(f"    {rid} :: {rn} [{sub}]")
