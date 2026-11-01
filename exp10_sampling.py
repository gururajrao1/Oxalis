"""Ugly pass 10: flux sampling of near-optimal states (core, glucose -10).

Settles the degenerate O2 12-14.7 question with distributions instead of single
solver paths: among states at >=95% optimal growth, how do PFL/PDH/formate vary?
Conditions: anaerobic (o2=0) and mid-transition (o2=14).
"""
import time

import cobra
from cobra.sampling import OptGPSampler

KEY = ["PFL", "PDH", "EX_for_e", "EX_ac_e", "EX_etoh_e", "ATPS4r"]


def sample_at(o2, tag, n=1000):
    m = cobra.io.load_model("textbook")
    m.reactions.EX_glc__D_e.lower_bound = -10.0
    m.reactions.EX_o2_e.lower_bound = -o2
    opt = m.slim_optimize()
    bio = next(r.id for r in m.reactions if "biomass" in r.id.lower())
    m.reactions.get_by_id(bio).lower_bound = 0.95 * opt
    KEY_OUT = KEY + [bio]
    t0 = time.time()
    s = OptGPSampler(m, processes=1, seed=42)
    df = s.sample(n)
    print(f"--- {tag}: {n} samples in {time.time()-t0:.0f}s (opt={opt:.4f}) ---")
    sub = df[[c for c in KEY_OUT if c in df.columns]]
    print(sub.describe().loc[["mean", "std", "min", "max"]].round(3).to_string())
    sub.to_csv(f"sampling_{tag}.csv", index=False)


if __name__ == "__main__":
    sample_at(0.0, "o2_0")
    sample_at(14.0, "o2_14")
