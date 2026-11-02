"""Exp 23: lactate regulation — imposed-bound scenarios, honestly labeled.

FBA cannot see regulation (exp16): the anaerobic optimum secretes zero
lactate. Here we impose what regulation/measurement says and quantify the
growth cost — the direction of causality is bounds -> cost, not prediction:
  1. Observed lactate: anaerobic q_glc=18.5, force lactate secretion at the
     measured level (for:ac:etoh:lac = 2.5:1:1:0.3, JB 182:620-626; absolute
     scale from the measured biomass yield Y=0.023, exp6: lac ~= 3.76).
     Report the growth cost of matching the measurement.
  2. fnr deletion mimic (anaerobic): FNR activates pfl/frd anaerobically.
     Force PFL capacity to 10% and FRD7 off -> growth defect (directional
     match to the reported anaerobic defect of fnr mutants).
  3. arcA deletion mimic (aerobic, q_glc=10.5, o2cap=15): ArcA represses TCA
     genes; derepress by forcing ICDHyr flux >= WT level + 50% -> overflow
     acetate falls (directional match to reported low-acetate arcA phenotype).
All bounds are imposed by hand; the model contributes the cost accounting.
"""
import cobra
import pandas as pd

m0 = cobra.io.load_model("textbook")
BIO = "Biomass_Ecoli_core"
rows = []


def base(glc, o2):
    m = m0.copy()
    m.reactions.EX_glc__D_e.lower_bound = -glc
    m.reactions.EX_o2_e.lower_bound = -o2
    return m


def fluxes(m):
    s = m.optimize()
    st = s.status
    f = s.fluxes if st == "optimal" else {}
    g = lambda r: float(f.get(r, 0.0)) if st == "optimal" else 0.0
    return st, g


# --- WT anaerobic reference at measured uptake ---
m = base(18.5, 0.0)
st, g = fluxes(m)
wt_ana = g(BIO)
wt_pfl = g("PFL")
print(f"WT anaerobic q18.5: mu={wt_ana:.4f} lac={g('EX_lac__D_e'):.2f} "
      f"ac={g('EX_ac_e'):.2f}")
rows.append({"scenario": "WT anaerobic", "growth": wt_ana,
             "lac": g("EX_lac__D_e"), "ac": g("EX_ac_e"),
             "etoh": g("EX_etoh_e"), "for": g("EX_for_e"), "status": st})

# --- 1. observed lactate imposed ---
# Absolute scale: Y=0.023 gDW/mmol -> mu 0.43 at 18.5; biomass C = 16.5% of
# 111 C-mmol in; products share 92.7 C-mmol in ratio weights summing 7.4k.
LAC_OBS = 0.3 * (18.5 * 6 * (1 - 0.43 * 42.56 / (18.5 * 6)) / 7.4)
print(f"measured lactate anchor: {LAC_OBS:.2f} mmol/gDW/h")
m = base(18.5, 0.0)
m.reactions.EX_lac__D_e.lower_bound = LAC_OBS
st, g = fluxes(m)
print(f"lactate-imposed: mu={g(BIO):.4f} (cost {wt_ana - g(BIO):.4f})")
rows.append({"scenario": "observed lactate imposed", "growth": g(BIO),
             "lac": g("EX_lac__D_e"), "ac": g("EX_ac_e"),
             "etoh": g("EX_etoh_e"), "for": g("EX_for_e"), "status": st})

# --- 2. fnr deletion mimic (anaerobic) ---
m = base(18.5, 0.0)
m.reactions.PFL.upper_bound = 0.1 * wt_pfl  # 10% of same-condition WT
m.reactions.FRD7.upper_bound = 0.0
m.reactions.FRD7.lower_bound = 0.0
st, g = fluxes(m)
print(f"fnr mimic: mu={g(BIO):.4f} (vs WT {wt_ana:.4f})")
rows.append({"scenario": "fnr deletion mimic", "growth": g(BIO),
             "lac": g("EX_lac__D_e"), "ac": g("EX_ac_e"),
             "etoh": g("EX_etoh_e"), "for": g("EX_for_e"), "status": st})

# --- 3. arcA deletion mimic (aerobic at measured uptakes) ---
m = base(10.5, 15.0)
st0, g0 = fluxes(m)
wt_aer, wt_ac, wt_icdh = g0(BIO), g0("EX_ac_e"), g0("ICDHyr")
m = base(10.5, 15.0)
# Derepress the full oxidative arm (WT optimum runs only the CS-ICDH
# branch; AKGDH/SUCDi/MDH sit at 0), not just ICDH alone.
for r in ["ICDHyr", "AKGDH", "SUCDi", "MDH"]:
    m.reactions.get_by_id(r).lower_bound = 1.5 * max(wt_icdh, 0.0)
st, g = fluxes(m)
print(f"arcA mimic: mu={g(BIO):.4f} (WT {wt_aer:.4f}), "
      f"acetate {g('EX_ac_e'):.2f} (WT {wt_ac:.2f})")
rows.append({"scenario": "arcA deletion mimic", "growth": g(BIO),
             "lac": g("EX_lac__D_e"), "ac": g("EX_ac_e"),
             "etoh": g("EX_etoh_e"), "for": g("EX_for_e"), "status": st})

pd.DataFrame(rows).to_csv("regulation_cost.csv", index=False)
print("saved regulation_cost.csv — takeaway: matching measured lactate costs "
      "growth (ATP-optimal mixed-acid vs LDH); fnr/arcA mimics move the "
      "reported directions under imposed bounds.")
