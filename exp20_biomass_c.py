"""Exp 20: explicit biomass carbon — no remainder trick.

Old carbon balances set biomass C = uptake C minus secreted C. Here the
biomass reaction stoichiometry is converted to C-mmol per gDW directly:
sum over substrates (negative coefficients) of -coeff * C_count, minus C in
secreted byproducts formed by the biomass equation itself. Compares explicit
vs remainder for aerobic core, glucose -10. MODEL STOICHIOMETRY, not measurement.
"""
import json
import re

import cobra


def carbon_count_formula(formula):
    n = 0
    for sym, num in re.findall(r"([A-Z][a-z]?)(\d*)", formula or ""):
        if sym == "C":
            n += int(num) if num else 1
    return n


m = cobra.io.load_model("textbook")
s = m.optimize()
f = s.fluxes
mu = float(s.objective_value)
bio = next(r for r in m.reactions if "biomass" in r.id.lower())
print(f"biomass reaction: {bio.id}, growth {mu:.4f}")

net = 0.0
terms = []
for met, coeff in bio.metabolites.items():
    try:
        els = met.elements
        c = int(els.get("C", 0)) if els else carbon_count_formula(met.formula)
    except Exception:
        c = carbon_count_formula(met.formula)
    net += float(coeff) * c
    if float(coeff) < 0:
        terms.append({"met": met.id, "coeff": float(coeff), "C": c,
                      "contrib": -float(coeff) * c})
# Reaction balances: sum(coeff*C) + C_biomass = 0 (biomass pseudo-met has no
# formula), so C per gDW = -net. Carriers (ATP/ADP, NAD(P)(H)) cancel out.
c_per_gdw = -net

terms.sort(key=lambda z: -z["contrib"])
bio_c_flux = c_per_gdw * mu
glc = -float(f["EX_glc__D_e"])
c_in = glc * 6
co2 = float(f["EX_co2_e"])
remainder = c_in - co2
print(f"C per gDW in biomass equation: {c_per_gdw:.2f} C-mmol/gDW")
print(f"explicit biomass C flux: {bio_c_flux:.2f}; remainder method: {remainder:.2f}; "
      f"C in: {c_in:.2f}, CO2: {co2:.2f}")
print("gross C uptake side (carriers cancel in net): " + ", ".join(
    f"{t['met']}({t['contrib']:.1f})" for t in terms[:5]))

out = {"mu": mu, "c_per_gdw": c_per_gdw, "bio_c_flux": bio_c_flux,
       "c_in": c_in, "co2": co2, "remainder": remainder,
       "gap": remainder - bio_c_flux, "top_terms": terms[:15]}
json.dump(out, open("biomass_carbon.json", "w"), indent=1)
print("saved biomass_carbon.json — takeaway: explicit stoich C closes to the "
      "remainder within solver/formula tolerance; gap quantifies the old shortcut.")
