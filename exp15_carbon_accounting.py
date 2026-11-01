"""Ugly pass 15: carbon accounting, aerobic core, glucose -10 (ONE condition).

Steps: C uptake; G6P split (PGI vs G6PDH2r); CO2 reaction inventory vs EX_co2;
balance closure; Sankey flows. MODEL PREDICTIONS, not measured fluxes.
"""
import json

import cobra

m = cobra.io.load_model("textbook")
s = m.optimize()
f = s.fluxes
glc = -float(f["EX_glc__D_e"])
C_IN = glc * 6
print(f"glucose uptake {glc:.2f} mmol -> C in = {C_IN:.2f} C-mmol")

pgi = float(f["PGI"])
g6 = float(f["G6PDH2r"])
print(f"G6P split: PGI {pgi:.2f} ({100*pgi/glc:.1f}%), G6PDH2r {g6:.2f} ({100*g6/glc:.1f}%)")

inv = []
for r in m.reactions:
    for met, coeff in r.metabolites.items():
        if met.id == "co2_c":
            inv.append({"reaction": r.id, "coeff": float(coeff),
                        "flux": float(f[r.id]),
                        "co2": float(coeff) * float(f[r.id])})
internal = [x for x in inv if x["reaction"] != "CO2t"]  # export is not production
prod = sum(x["co2"] for x in internal if x["co2"] > 0)
cons = sum(x["co2"] for x in internal if x["co2"] < 0)
net = prod + cons
ex = float(f["EX_co2_e"])
print("--- CO2 inventory (positive = produced) ---")
for x in sorted(inv, key=lambda z: -z["co2"]):
    print(f"{x['reaction']:12s} coeff={x['coeff']:+.0f} flux={x['flux']:+8.2f} co2={x['co2']:+8.2f}")
print(f"produced={prod:.2f} consumed={cons:.2f} net={net:.2f} vs EX_co2_e={ex:.2f} "
      f"match={abs(net-ex) < 1e-6}")

C_CO2 = ex  # co2 is C1
C_BIO = C_IN - C_CO2
print(f"balance: in={C_IN:.2f} = biomass {C_BIO:.2f} ({100*C_BIO/C_IN:.1f}%) "
      f"+ CO2 {C_CO2:.2f} ({100*C_CO2/C_IN:.1f}%), residual 0.00 by construction "
      f"(biomass C is the remainder: no carbon secreted except CO2)")

out = {"c_in": C_IN, "glc": glc, "pgi": pgi, "g6pdh": g6,
       "pgi_pct": 100 * pgi / glc, "g6pdh_pct": 100 * g6 / glc,
       "co2_reactions": inv, "co2_net": net, "ex_co2": ex,
       "c_co2": C_CO2, "c_biomass": C_BIO,
       "sankey": {"glc_c": C_IN, "pgi_c": pgi * 6, "ppp_c": g6 * 6,
                  "other_c": (glc - pgi - g6) * 6, "bio_c": C_BIO, "co2_c": C_CO2}}
json.dump(out, open("carbon_accounting.json", "w"), indent=1)
print("saved carbon_accounting.json")
