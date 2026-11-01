"""Ugly pass 6: experimental anchor. Simulate at Varma&Palsson 1994 measured uptakes
and score core + iML1515 predictions vs observations.

Observed (E. coli W3110, glucose minimal batch):
  aerobic:   q_glc=10.5, o2max=15, mu=0.68, Y=0.064 gDW/mmol (0.355 gDW/g)
  anaerobic: q_glc=18.5, mu=0.43, Y=0.023 gDW/mmol
  anaerobic molar ratio for:ac:etoh:lac = 2.5:1:1:0.3 (JB 182:620-626, K-12)
"""
import cobra
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

OBS = {"aer_mu": 0.68, "aer_Y": 0.064, "ana_mu": 0.43, "ana_Y": 0.023,
       "r_for": 2.5, "r_ac": 1.0, "r_etoh": 1.0, "r_lac": 0.3}


def sim(model_id, glc, o2cap):
    m = (cobra.io.load_model("textbook") if model_id == "core"
         else cobra.io.load_json_model("iML1515.json"))
    m.reactions.EX_glc__D_e.lower_bound = -glc
    m.reactions.EX_o2_e.lower_bound = -o2cap
    s = m.optimize()
    return m, s


rows = []
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.5))
x_mu = ["aerobic mu", "anaerobic mu"]
obs_mu = [OBS["aer_mu"], OBS["ana_mu"]]
pred = {"core": [], "1515": []}
for mid in ["core", "1515"]:
    # aerobic at measured uptakes
    m, s = sim(mid, 10.5, 15.0)
    mu, ac = float(s.objective_value), float(s.fluxes["EX_ac_e"])
    Y = mu / 10.5
    pred[mid] = [mu]
    rows += [(mid, "aer_mu", mu, OBS["aer_mu"]), (mid, "aer_Y", Y, OBS["aer_Y"])]
    print(f"{mid} aerobic@VP: mu={mu:.3f} (obs 0.68) Y={Y:.4f} (obs 0.064) acetate={ac:.2f}")
    # anaerobic at measured uptake
    m, s = sim(mid, 18.5, 0.0)
    mu = float(s.objective_value)
    Y = mu / 18.5
    pred[mid].append(mu)
    rows += [(mid, "ana_mu", mu, OBS["ana_mu"]), (mid, "ana_Y", Y, OBS["ana_Y"])]
    f = s.fluxes
    per = {p: float(f[f"EX_{p}_e"]) / 18.5 for p in ["for", "ac", "etoh", "lac__D"]}
    print(f"{mid} anaerobic@VP: mu={mu:.3f} (obs 0.43) Y={Y:.4f} (obs 0.023)")
    print(f"  per-glc yields: " + " ".join(f"{k}={v:.2f}" for k, v in per.items()))
    for k in per:
        rows.append((mid, f"y_{k}", per[k], None))

sc = pd.DataFrame(rows, columns=["model", "metric", "predicted", "observed"])
sc["err_pct"] = (sc["predicted"] - sc["observed"]).abs() / sc["observed"] * 100
sc.to_csv("anchor_scorecard.csv", index=False)
print(sc.to_string(index=False))

# plot 1: growth rates obs vs pred
w = 0.22
xs = range(2)
a1.bar([x - w for x in xs], obs_mu, w, label="observed (W3110)")
a1.bar(xs, pred["core"], w, label="core")
a1.bar([x + w for x in xs], pred["1515"], w, label="iML1515")
a1.set_xticks(list(xs), x_mu)
a1.set_ylabel("growth rate (1/h)")
a1.set_title("growth at measured uptakes: obs vs FBA")
a1.legend(fontsize=8)
# plot 2: anaerobic product ratios (per glucose), obs molar ratio scaled to ac=1
for_ = sc.query("metric=='y_for'")["predicted"].tolist()
ac = sc.query("metric=='y_ac'")["predicted"].tolist()
et = sc.query("metric=='y_etoh'")["predicted"].tolist()
la = sc.query("metric=='y_lac__D'")["predicted"].tolist()
labels = ["formate", "acetate", "ethanol", "lactate"]
obs_r = [OBS["r_for"], OBS["r_ac"], OBS["r_etoh"], OBS["r_lac"]]
core_r = [for_[0] / ac[0], 1.0, et[0] / ac[0], la[0] / ac[0]]
r1515 = [for_[1] / ac[1], 1.0, et[1] / ac[1], la[1] / ac[1]]
xs = range(4)
a2.bar([x - w for x in xs], obs_r, w, label="observed")
a2.bar(xs, core_r, w, label="core")
a2.bar([x + w for x in xs], r1515, w, label="iML1515")
a2.set_xticks(list(xs), labels)
a2.set_ylabel("mol / mol acetate")
a2.set_title("anaerobic product ratios")
a2.legend(fontsize=8)
fig.tight_layout()
fig.savefig("anchor.png", dpi=120)
print("saved anchor.png")
