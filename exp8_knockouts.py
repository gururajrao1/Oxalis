"""Ugly pass 8: single-gene knockout screen on iML1515 (aerobic + anaerobic,
glucose -10), validated against DEG essential genes (Keio/PEC E. coli).

Caveat on record: DEG essentiality is measured on RICH medium; our screen is on
glucose MINIMAL, so amino-acid biosynthesis genes will (correctly) show as
predicted-essential / observed-viable. That pattern itself is a validation.
"""
import cobra
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from cobra.flux_analysis.deletion import single_gene_deletion

# ---------- 1. DEG E. coli essential symbols ----------
ann = pd.read_csv("deg/deg_annotation_p.csv", sep=";", header=None, dtype=str,
                  quotechar='"')
ann.columns = ["degbook", "degid", "gene", "gi", "cog", "class", "function",
               "organism", "accession", "condition", "col11", "go", "uniprot",
               "col14"]
ecoli = ann[ann["organism"].str.contains("Escherichia coli", na=False)]
print("--- DEG E. coli records ---")
print(ecoli.groupby("organism")["gene"].count().to_string())
ess_syms = set(g.strip().lower() for g in ecoli["gene"].dropna())
print(f"union of E. coli essential symbols: {len(ess_syms)}")

# ---------- 2. map symbols -> iML1515 genes ----------
m0 = cobra.io.load_json_model("iML1515.json")
sym2gene = {}
for g in m0.genes:
    for cand in {g.id.lower(), (g.name or "").lower()}:
        sym2gene.setdefault(cand, g.id)
mapped = {s for s in ess_syms if s in sym2gene}
print(f"DEG symbols mapped to model genes: {len(mapped)}/{len(ess_syms)} "
      f"({len(ess_syms - mapped)} unmapped, mostly non-metabolic/strain-specific)")
sets = {}
for key in ["Escherichia coli MG1655 II", "Escherichia coli MG1655 I"]:
    s = set(g.strip().lower()
            for g in ecoli.loc[ecoli["organism"] == key, "gene"].dropna())
    sets[key] = {sym2gene[x] for x in s if x in sym2gene}
    print(f"{key}: {len(s)} symbols, {len(sets[key])} mapped to model")
sets["MG1655 I+II"] = (sets["Escherichia coli MG1655 I"]
                       | sets["Escherichia coli MG1655 II"])

# ---------- 3. screens ----------
def screen(o2_lb, tag, wt):
    m = cobra.io.load_json_model("iML1515.json")
    m.reactions.EX_glc__D_e.lower_bound = -10.0
    m.reactions.EX_o2_e.lower_bound = o2_lb
    wt_g = wt if wt else m.slim_optimize()
    res = single_gene_deletion(m, processes=1)
    res = res.copy()
    res["frac"] = res["growth"] / wt_g
    res["essential"] = res["frac"] < 0.01
    res.to_csv(f"ko_1515_{tag}.csv")
    print(f"--- {tag}: WT={wt_g:.4f} essentials={int(res['essential'].sum())}/{len(res)} ---")
    return res, wt_g

aer, wt_a = screen(-1000.0, "aerobic", 0.0)
ana, wt_n = screen(0.0, "anaerobic", 0.0)

# ---------- 4. confusion matrix (aerobic screen vs DEG) ----------
def first_id(x):
    return x if isinstance(x, str) else next(iter(x))


pred_ess = set(aer.loc[aer["essential"], "ids"].apply(first_id))
print(f"predicted essentials (aerobic): {len(pred_ess)}")
universe = set(aer["ids"].apply(first_id))
names = {g.id: (g.name or g.id) for g in m0.genes}
mat_rows = []
for label, ess_model in sets.items():
    TP = len(pred_ess & ess_model)
    FP = len(pred_ess - ess_model)
    FN = len(ess_model & universe - pred_ess)
    TN = len(universe - pred_ess - ess_model)
    acc = (TP + TN) / len(universe)
    prec = TP / (TP + FP) if TP + FP else 0
    rec = TP / (TP + FN) if TP + FN else 0
    print(f"[{label}] TP={TP} FP={FP} FN={FN} TN={TN} "
          f"acc={acc:.3f} prec={prec:.3f} rec={rec:.3f}")
    mat_rows.append({"set": label, "TP": TP, "FP": FP, "FN": FN, "TN": TN,
                     "acc": acc, "precision": prec, "recall": rec})
    if label == "Escherichia coli MG1655 II":
        fp = sorted(names.get(g, g) for g in pred_ess - ess_model)
        fn = sorted(names.get(g, g) for g in ess_model & universe - pred_ess)
        print(f"  FP sample ({len(fp)}): {fp[:40]}")
        print(f"  FN sample ({len(fn)}): {fn[:40]}")
        fig, ax = plt.subplots()
        ax.matshow([[TP, FN], [FP, TN]], cmap="Blues")  # rows=DEG, cols=pred
        for (i, j), v in [((0, 0), TP), ((0, 1), FN),
                          ((1, 0), FP), ((1, 1), TN)]:
            ax.text(j, i, str(v), ha="center", va="center", fontsize=14)
        ax.set_xticks([0, 1], ["pred ess", "pred viable"])
        ax.set_yticks([0, 1], ["DEG ess", "DEG viable"])
        ax.set_title(f"KO essentiality: iML1515 vs DEG MG1655-II (acc={acc:.2f})")
        fig.tight_layout()
        fig.savefig("ko_confusion.png", dpi=120)
        print("saved ko_confusion.png")
pd.DataFrame(mat_rows).to_csv("ko_confusion.csv", index=False)

# ---------- 5. conditional essentials + redox-sick KOs ----------
def gid(x):
    if isinstance(x, str):
        return x
    return next(iter(x))


a_frac = {gid(i): f for i, f in zip(aer["ids"], aer["frac"])}
n_frac = {gid(i): f for i, f in zip(ana["ids"], ana["frac"])}
a_ess = {g for g, f in a_frac.items() if f < 0.01}
n_ess = {g for g, f in n_frac.items() if f < 0.01}
print(f"essential in both: {len(a_ess & n_ess)}")
print(f"aerobic-only essentials: {sorted(a_ess - n_ess)}")
print(f"anaerobic-only essentials ({len(n_ess - a_ess)}): {sorted(n_ess - a_ess)}")
for g in sorted(n_ess - a_ess):
    gene = m0.genes.get_by_id(g)
    rxns = sorted({r.id for r in gene.reactions})
    print(f"  {g} ({gene.name}): {rxns}")
sick = sorted([(g, a_frac[g], n_frac[g]) for g in universe - a_ess - n_ess
               if a_frac[g] > 0.9 and n_frac[g] < 0.5], key=lambda t: t[2])
print(f"sick-only-anaerobically (aer>90%, ana<50%): {len(sick)}")
for g, fa, fn in sick[:20]:
    print(f"  {g} aer={fa:.2f} ana={fn:.2f}")
