"""Exp 22: fit kLa + Monod constants to a real batch curve.

Target data (all with provenance):
  - Enjalbert, Letisse & Portais, Metabolites 2013 (PMC3901295): MG1655,
    M9 + 15 mM glucose, aerobic bioreactor, DOT > 20%. Acetate peak at GE =
    8.6% of 90 C-mmol -> 3.87 mM; acetate gone ~3 h after GE; biomass 54.8%
    of C -> 49.32 C-mmol, ~1.16 gDW/L with the core biomass carbon
    (42.56 C-mmol/gDW, exp20; composition caveat noted).
  - mu_exp = 0.57 h-1: MG1655 glucose-bioreactor exponential rate from the
    feast-famine study (16 mM glucose, mSphere 2020, Fig. 1A: 0.57 h-1,
    4 mM acetate in P1). Same strain, same regime; NOT from Enjalbert.
Fit: coordinate descent on (vmax_glc, vmax_ac, o2cap) with kLa fixed at a
stirred-tank value; kLa reported as a lower bound (DOT > 20% constraint),
since any large kLa is indistinguishable in well-aerated data.
Requires the exp18 semi-implicit O2 pool (explicit Euler goes phantom
anaerobic for kLa*dt > 1 and uncapped-supersaturating otherwise).
"""
import json
import math
import warnings

import pandas as pd

from exp18_kla import run_dfba_kla

warnings.filterwarnings("ignore")

GLC0 = 15.0
KLA_FIXED = 400.0  # stirred tank; checked post-fit via o2_min_frac >= 0.2
TARGETS = {"ac_peak": 3.87, "t_ac_after_ge": 3.0, "X_ge": 1.16, "mu_exp": 0.57}
BASE = dict(glc0=GLC0, X0=0.05, dt=0.2, T=14.0, km=0.02,
            vmax_o2=20.0, ks_o2=0.01, o2star=0.2, o2_0=0.2, kla=KLA_FIXED)


def features(rows):
    df = pd.DataFrame(rows)
    ge = df.loc[df["glc"] < 0.05, "t"]
    t_ge = float(ge.min()) if len(ge) else float("nan")
    pre = df if math.isnan(t_ge) else df[df["t"] <= t_ge + 1e-9]
    ac_peak = float(pre["ac"].max())
    post = df if math.isnan(t_ge) else df[df["t"] > t_ge]
    # Clearance = fall below 5% of peak: at low mM the max-growth LP goes
    # degenerate (acetate uptake no longer buys growth) and leaves a dreg
    # that a fixed 0.05 mM cutoff would call "never consumed".
    gone = post.loc[post["ac"] < 0.05 * ac_peak, "t"]
    t_ac = (float(gone.min()) - t_ge) if (len(gone) and not math.isnan(t_ge)) else float("nan")
    mu_exp = float(pre["mu"].mean())
    return {"ac_peak": ac_peak, "t_ac_after_ge": t_ac,
            "X_ge": float(pre["X"].iloc[-1]), "mu_exp": mu_exp, "t_ge": t_ge,
            "o2_min_frac": float(df["o2"].min() / BASE["o2star"])}


def simulate(vmax_glc, vmax_ac, o2cap, dt=0.2):
    # o2cap is the cell-physiology respiratory cap (V&P measured o2max=15
    # aerobically, exp6): it trades growth rate against overflow acetate,
    # so it is fitted, not fixed. kLa stays fixed-high (stirred tank) and is
    # reported as a lower bound from the DOT > 20% constraint.
    return run_dfba_kla(**dict(BASE, vmax_glc=vmax_glc, vmax_ac=vmax_ac,
                               o2cap=o2cap, dt=dt, scavenge=True))


def loss(p, targets=TARGETS, dt=0.2):
    f = features(simulate(*p, dt=dt))
    if any(math.isnan(f[k]) for k in targets):
        return 1e6
    return sum(((f[k] - targets[k]) / targets[k]) ** 2 for k in targets)


def fit(start, steps, rounds=8, dt=0.2, targets=TARGETS, kicks=25, seed=1):
    import random
    rng = random.Random(seed)
    best = list(start)
    best_L = loss(best, targets=targets, dt=dt)
    for _ in range(rounds):
        improved = False
        for i in range(len(best)):
            for mult in (1 + steps[i], 1 / (1 + steps[i])):
                cand = list(best)
                cand[i] = max(1e-6, cand[i] * mult)
                L = loss(cand, targets=targets, dt=dt)
                if L < best_L:
                    best, best_L = cand, L
                    improved = True
        if not improved:
            steps = [s / 2 for s in steps]
    for _ in range(kicks):  # basin-hopping-lite: random log-kicks
        cand = [max(1e-6, b * math.exp(rng.uniform(-0.5, 0.5))) for b in best]
        L = loss(cand, targets=targets, dt=dt)
        if L < best_L:
            best, best_L = cand, L
            best, best_L = fit(best, [0.2] * len(best), rounds=4,
                               dt=dt, targets=targets, kicks=0)
    return best, best_L


def recovery_test():
    # Truth in the identifiable zone (vmax_ac low enough that clearance
    # time responds to it; very large vmax_ac is a known flat direction).
    truth = [8.0, 2.0, 15.0]
    synth = features(simulate(*truth))
    tgt = {k: synth[k] for k in TARGETS}
    got, L = None, 1e18
    for start in ([11.0, 6.0, 22.0], [6.0, 1.0, 10.0], [9.5, 4.0, 18.0]):
        b, l = fit(start, [0.4, 0.4, 0.4], rounds=8, targets=tgt)
        if l < L:
            got, L = b, l
    return truth, tgt, got, L


def kla_lower_bound(vmax_glc, vmax_ac, o2cap=22.0,
                    grid=(400, 200, 100, 50, 30, 20, 10)):
    """Smallest kLa keeping dissolved O2 above the reported DOT > 20%."""
    for kla in sorted(grid):
        rows = run_dfba_kla(**dict(BASE, vmax_glc=vmax_glc, vmax_ac=vmax_ac,
                                   o2cap=o2cap, kla=float(kla)))
        if min(r["o2"] for r in rows) / BASE["o2star"] >= 0.2:
            return float(kla)
    return None


if __name__ == "__main__":
    truth, tgt, got, rec_L = recovery_test()
    print("recovery: truth %s -> got %s (loss %.2e)" %
          (["%.2f" % v for v in truth], ["%.2f" % v for v in got], rec_L))
    print("default-params loss: %.4f" % loss([10.5, 6.0, 15.0]))
    best, L = None, 1e18
    for start in ([10.5, 6.0, 15.0], [7.0, 8.0, 22.0], [12.0, 2.0, 20.0]):
        b, l = fit(start, [0.4, 0.4, 0.4], rounds=10)
        print("  start %s -> %s loss=%.5f" % (start, [round(v, 3) for v in b], l))
        if l < L:
            best, L = b, l
    print("fitted vmax_glc=%.3f vmax_ac=%.3f o2cap=%.2f loss=%.5f" % (*best, L))
    ff = features(simulate(*best, dt=0.05))
    print("fine-sim:", {k: round(v, 3) for k, v in ff.items()})
    klo = kla_lower_bound(*best)
    print("kLa lower bound for DOT>20%%: %s (fit used %g)" % (klo, KLA_FIXED))
    json.dump({"vmax_glc": best[0], "vmax_ac": best[1], "o2cap": best[2],
               "kla_used": KLA_FIXED, "kla_lower_bound": klo,
               "loss": L, "features": ff, "targets": TARGETS,
               "provenance": "ac/X/t_ac: Enjalbert et al. 2013 PMC3901295; "
                             "mu: feast-famine mSphere 2020 (0.57 h-1)"},
              open("kla_fit.json", "w"), indent=1)
    print("saved kla_fit.json")
