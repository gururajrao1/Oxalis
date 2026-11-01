"""Ugly pass 11: dynamic FBA batch simulator (core model, static optimization).

Euler integration: at each step, Monod uptake bounds from extracellular
concentrations, FBA for mu + exchange fluxes, update biomass/metabolites.
Limitations on record: O2 is a flux cap (no gas-transfer balance); maintenance
is the model's default; Monod constants are plausible, not fitted.
"""
import cobra


def run_dfba(o2cap=15.0, glc0=10.0, X0=0.05, dt=0.05, T=14.0, anaerobic=False,
             vmax_glc=10.5, km=0.02, vmax_ac=6.0):
    m = cobra.io.load_model("textbook")
    m.reactions.EX_o2_e.lower_bound = 0.0 if anaerobic else -o2cap
    X, glc, ac, for_, etoh, t = X0, glc0, 0.0, 0.0, 0.0, 0.0
    rows = []
    while t <= T + 1e-9:
        m.reactions.EX_glc__D_e.lower_bound = -vmax_glc * glc / (km + glc) if glc > 0 else 0.0
        m.reactions.EX_ac_e.lower_bound = -vmax_ac * ac / (km + ac) if ac > 0 else 0.0
        s = m.optimize()
        mu = float(s.objective_value) if s.status == "optimal" else 0.0
        f = s.fluxes if s.status == "optimal" else {}
        g = lambda r: float(f.get(r, 0.0))
        rows.append({"t": round(t, 3), "X": X, "glc": glc, "ac": ac,
                     "for": for_, "etoh": etoh, "mu": mu})
        # Euler update (fluxes in mmol/gDW/h, X in g/L, pools in mM)
        glc = max(0.0, glc + g("EX_glc__D_e") * X * dt)
        ac = max(0.0, ac + g("EX_ac_e") * X * dt)
        for_ = max(0.0, for_ + g("EX_for_e") * X * dt)
        etoh = max(0.0, etoh + g("EX_etoh_e") * X * dt)
        X = X + mu * X * dt
        t += dt
    return rows


def run_dfba_anaerobic(glc0=10.0, X0=0.05, dt=0.05, T=20.0, vmax_glc=18.5, km=0.02):
    m = cobra.io.load_model("textbook")
    m.reactions.EX_o2_e.lower_bound = 0.0
    X, glc, ac, for_, etoh, t = X0, glc0, 0.0, 0.0, 0.0, 0.0
    rows = []
    while t <= T + 1e-9:
        m.reactions.EX_glc__D_e.lower_bound = -vmax_glc * glc / (km + glc) if glc > 0 else 0.0
        s = m.optimize()
        mu = float(s.objective_value) if s.status == "optimal" else 0.0
        f = s.fluxes if s.status == "optimal" else {}
        g = lambda r: float(f.get(r, 0.0))
        rows.append({"t": round(t, 3), "X": X, "glc": glc, "ac": ac,
                     "for": for_, "etoh": etoh, "mu": mu})
        glc = max(0.0, glc + g("EX_glc__D_e") * X * dt)
        ac = max(0.0, ac + g("EX_ac_e") * X * dt)
        for_ = max(0.0, for_ + g("EX_for_e") * X * dt)
        etoh = max(0.0, etoh + g("EX_etoh_e") * X * dt)
        X = X + mu * X * dt
        t += dt
    return rows


if __name__ == "__main__":
    import pandas as pd
    aer = pd.DataFrame(run_dfba())
    aer.to_csv("dfba_aerobic.csv", index=False)
    ana = pd.DataFrame(run_dfba_anaerobic())
    ana.to_csv("dfba_anaerobic.csv", index=False)
    print("aerobic: X0->Xend %.3f->%.3f, peak acetate %.2f mM, glc depleted at t=%.2f" % (
        aer["X"].iloc[0], aer["X"].iloc[-1], aer["ac"].max(),
        aer.loc[aer["glc"] < 0.05, "t"].min()))
    print("anaerobic: X0->Xend %.3f->%.3f, end ac/for/etoh %.1f/%.1f/%.1f mM" % (
        ana["X"].iloc[0], ana["X"].iloc[-1], ana["ac"].iloc[-1],
        ana["for"].iloc[-1], ana["etoh"].iloc[-1]))
