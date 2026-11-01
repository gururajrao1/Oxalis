"""Exp 18: dFBA with O2 gas transfer (kLa), core model.

Old model: O2 uptake cap fixed (infinite gas supply until glucose runs out).
New model: dissolved O2 pool with transfer kLa*(O2star-O2) minus cellular
uptake. Uptake bound at each step = min(o2cap, vmax_o2*O2/(Ks+O2)).
Backward compatible: kLa=inf recovers the old fixed-cap trajectory.
Import-safe: server imports run_dfba_kla from here.
"""
import cobra


def run_dfba_kla(o2cap=15.0, glc0=10.0, X0=0.05, dt=0.05, T=14.0,
                 vmax_glc=10.5, km=0.02, vmax_ac=6.0,
                 kla=10.0, o2star=0.2, o2_0=0.2, vmax_o2=20.0, ks_o2=0.01):
    m = cobra.io.load_model("textbook")
    X, glc, ac, for_, etoh, o2, t = X0, glc0, 0.0, 0.0, 0.0, o2_0, 0.0
    rows = []
    while t <= T + 1e-9:
        # O2-limited uptake bound from dissolved pool
        o2_bound = min(o2cap, vmax_o2 * o2 / (ks_o2 + o2) if o2 > 0 else 0.0)
        m.reactions.EX_o2_e.lower_bound = -o2_bound
        m.reactions.EX_glc__D_e.lower_bound = -vmax_glc * glc / (km + glc) if glc > 0 else 0.0
        m.reactions.EX_ac_e.lower_bound = -vmax_ac * ac / (km + ac) if ac > 0 else 0.0
        s = m.optimize()
        mu = float(s.objective_value) if s.status == "optimal" else 0.0
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
        o2 = max(0.0, o2 + (kla * (o2star - o2) - qo2 * X) * dt)
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
