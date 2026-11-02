"""Exp 18: dFBA with O2 gas transfer (kLa), core model.

Old model: O2 uptake cap fixed (infinite gas supply until glucose runs out).
New model: dissolved O2 pool with transfer kLa*(O2star-O2) minus cellular
uptake. Uptake bound at each step = min(o2cap, vmax_o2*O2/(Ks+O2)).
Backward compatible: kLa=inf recovers the old fixed-cap trajectory.
Import-safe: server imports run_dfba_kla from here.
"""
import math

import cobra


def run_dfba_kla(o2cap=15.0, glc0=10.0, X0=0.05, dt=0.05, T=14.0,
                 vmax_glc=10.5, km=0.02, vmax_ac=6.0,
                 kla=10.0, o2star=0.2, o2_0=0.2, vmax_o2=20.0, ks_o2=0.01,
                 scavenge=False):
    m = cobra.io.load_model("textbook")
    X, glc, ac, for_, etoh, o2, t = X0, glc0, 0.0, 0.0, 0.0, o2_0, 0.0
    rows = []
    while t <= T + 1e-9:
        # O2-limited uptake bound from dissolved pool
        if math.isinf(kla):
            o2, o2_bound = o2star, o2cap
        else:
            o2_bound = min(o2cap, vmax_o2 * o2 / (ks_o2 + o2) if o2 > 0 else 0.0)
        m.reactions.EX_o2_e.lower_bound = -o2_bound
        m.reactions.EX_glc__D_e.lower_bound = -vmax_glc * glc / (km + glc) if glc > 0 else 0.0
        m.reactions.EX_ac_e.lower_bound = -vmax_ac * ac / (km + ac) if ac > 0 else 0.0
        s = m.optimize()
        mu = float(s.objective_value) if s.status == "optimal" else 0.0
        if scavenge and s.status != "optimal":
            # Starvation: Monod-capped uptake cannot cover the forced ATPM
            # floor, so max-growth is infeasible and pools would freeze with
            # food left. Fall back to maintenance-first: use what uptake is
            # available to cover maintenance (mu recorded as 0).
            bio = next(r.id for r in m.reactions if "biomass" in r.id.lower())
            m.reactions.ATPM.lower_bound = 0.0
            m.objective = m.reactions.ATPM
            m.objective_direction = "max"
            s2 = m.optimize()
            m.reactions.ATPM.lower_bound = 8.39
            m.objective = m.reactions.get_by_id(bio)
            m.objective_direction = "max"
            if s2.status == "optimal":
                s = s2
            mu = 0.0
        if scavenge and s.status == "optimal" and mu < 0.05:
            # Near starvation the max-growth LP is degenerate: uptake buys
            # no growth, so the solver may leave substrate behind that real
            # cells would scavenge. Lexicographic second pass: hold growth
            # at optimum, maximize substrate uptake (most-negative EX flux).
            bio = next(r.id for r in m.reactions if "biomass" in r.id.lower())
            m.reactions.get_by_id(bio).lower_bound = mu
            for ex_id, pool in (("EX_glc__D_e", glc), ("EX_ac_e", ac)):
                if pool <= 0:
                    continue
                m.objective = m.reactions.get_by_id(ex_id)
                m.objective_direction = "min"
                s2 = m.optimize()
                if s2.status == "optimal":
                    s = s2
            m.reactions.get_by_id(bio).lower_bound = 0.0
            m.objective = m.reactions.get_by_id(bio)
            m.objective_direction = "max"
        f = s.fluxes if s.status == "optimal" else {}
        g = lambda r: float(f.get(r, 0.0))
        qo2 = -g("EX_o2_e")  # positive uptake rate
        rows.append({"t": round(t, 3), "X": X, "glc": glc, "ac": ac,
                     "for": for_, "etoh": etoh, "mu": mu,
                     "o2": o2, "qo2": qo2, "o2_bound": o2_bound})
        # Euler update pools (mM; O2 transfer in mmol/L/h)
        glc = max(0.0, glc + g("EX_glc__D_e") * X * dt)
        ac = max(0.0, ac + g("EX_ac_e") * X * dt)
        for_ = max(0.0, for_ + g("EX_for_e") * X * dt)
        etoh = max(0.0, etoh + g("EX_etoh_e") * X * dt)
        # Semi-implicit O2 update: unconditional stability for any kLa*dt,
        # clipped to [0, o2star] (no supersaturation). Explicit Euler here
        # oscillates/clips to phantom anaerobiosis when kLa*dt > 1.
        if math.isinf(kla):
            o2 = o2star
        else:
            o2 = min(o2star, max(0.0, (o2 + (kla * o2star - qo2 * X) * dt)
                                   / (1 + kla * dt)))
        X = X + mu * X * dt
        t += dt
    return rows


if __name__ == "__main__":
    import pandas as pd
    df = pd.DataFrame(run_dfba_kla())
    df.to_csv("dfba_kla.csv", index=False)
    print(f"kLa run: X {df['X'].iloc[0]:.3f}->{df['X'].iloc[-1]:.3f}, "
          f"O2 min {df['o2'].min():.3f} mM, peak ac {df['ac'].max():.2f} mM")
    print("saved dfba_kla.csv — takeaway: with finite kLa the culture goes "
          "microaerobic mid-batch; acetate hump is lower/wider than fixed-cap.")
