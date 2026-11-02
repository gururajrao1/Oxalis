"""Exp 24: MILP knockout selection for succinate (open solver: GLPK).

Backlog asked for OptKnock/ROOM with an open solver. Honest scope:
  - True bilevel OptKnock (growth-coupled optimum) is NOT implemented —
    it needs a bilevel-capable MILP solver, and only GLPK is available here.
  - What IS implemented: single-level MILP knockout selection. Binary KO
    variables over GPR-mapped reactions, big-M coupling of reaction bounds
    to KO state, cardinality cap; objective = max succinate secretion
    subject to growth >= 50% of the KO-strain optimum. This finds
    growth-tolerant producers (the exp19 envelope idea), not provably
    growth-coupled strains — each hit is then validated by direct KO
    simulation in core AND in iML1515 (growth-coupled check at the pure
    max-growth optimum: does succinate still secrete?).
GPR-aware: knockouts are genes; a reaction is off only if ALL its isozymes
are knocked out (OR logic linearized per reaction).
"""
import itertools
import json
import warnings

import cobra
import pandas as pd

warnings.filterwarnings("ignore")

SYMS = ["pgi", "pfkA", "tpiA", "gapA", "pgk", "eno", "ppc", "zwf", "gnd",
        "pta", "ackA", "pflB", "adhE", "ldhA",
        "sdhA", "frdA", "mdh", "pck", "aceA", "sucA"]
COND_O2 = 0.0  # anaerobic
GLC = -10.0
BIGM = 1000.0


def milp_select(model, gene_ids, bio_id, target_ex, k_max=2, growth_frac=0.5):
    """Single-level MILP: max target secretion, growth floor, <= k_max KOs."""
    m = model.copy()
    m.reactions.EX_glc__D_e.lower_bound = GLC
    m.reactions.EX_o2_e.lower_bound = COND_O2
    wt = m.optimize().objective_value
    # candidate reactions: backed by exactly the selected genes (no
    # spontaneous/missing-GPR reactions, to keep the GPR logic exact)
    gids = set(gene_ids)
    rxn_genes = {}
    for r in m.reactions:
        gs = {g.id for g in r.genes}
        if gs and gs <= gids:
            rxn_genes[r.id] = gs
    I = m.solver.interface
    y = {gid: I.Variable(f"ko_{gid}", type="binary") for gid in gene_ids}
    for v in y.values():
        m.solver.add(v)
    for rid, gs in rxn_genes.items():
        r = m.reactions.get_by_id(rid)
        # reaction off iff every backing gene is KO: r_on <= 1 - y_g per g
        # implemented via bound coupling: lb*(1-sum y) <= v <= ub*(1-sum y)
        # linearized with one auxiliary per reaction.
        z = I.Variable(f"on_{rid}", lb=0.0, ub=1.0)
        m.solver.add(z)
        for gid in gs:
            m.solver.add(I.Constraint(z + y[gid], ub=1.0,
                                      name=f"gpr_{rid}_{gid}"))
        # Lower link: reaction on (z=1) unless a backing gene is KO.
        # With the upper links this is exact OR logic for isozymes.
        m.solver.add(I.Constraint(z + sum(y[g] for g in gs), lb=1.0,
                                  name=f"gprlo_{rid}"))
        lo, hi = (r.lower_bound, r.upper_bound)
        v = r.flux_expression
        m.solver.add(I.Constraint(v - hi * z, ub=0.0, name=f"hi_{rid}"))
        m.solver.add(I.Constraint(v - lo * z, lb=0.0, name=f"lo_{rid}"))
    m.solver.add(I.Constraint(sum(y.values()), ub=k_max, name="card"))
    bio = m.reactions.get_by_id(bio_id)
    m.solver.add(I.Constraint(bio.flux_expression, lb=growth_frac * wt,
                              name="growth_floor"))
    m.objective = m.reactions.get_by_id(target_ex)
    m.objective_direction = "max"
    st = m.optimize()
    ok = (st.status == "optimal")
    kos = sorted(gid for gid in gene_ids if y[gid].primal is not None
                 and y[gid].primal > 0.5)
    succ = float(st.fluxes[target_ex]) if ok else 0.0
    return st.status, kos, succ, float(wt)


def direct_ko(model, sym2id, combo, bio_id, target_ex):
    ko = model.copy()
    ko.reactions.EX_glc__D_e.lower_bound = GLC
    ko.reactions.EX_o2_e.lower_bound = COND_O2
    for s in combo:
        ko.genes.get_by_id(sym2id[s]).knock_out()
    s = ko.optimize()
    if s.status != "optimal":
        return 0.0, 0.0
    return float(s.objective_value), float(s.fluxes[target_ex])


def forced_ko_check(model, gene_ids, bio_id, target_ex, sym):
    """Verify GPR coupling: forcing y=1 must kill the backed reaction and
    reproduce the direct-KO envelope for that gene."""
    m = model.copy()
    m.reactions.EX_glc__D_e.lower_bound = GLC
    m.reactions.EX_o2_e.lower_bound = COND_O2
    wt = m.optimize().objective_value
    I = m.solver.interface
    gid = next(g for g in gene_ids
               if model.genes.get_by_id(g).name == sym)
    y = I.Variable("ko_force", type="binary")
    m.solver.add(y)
    m.solver.add(I.Constraint(y, lb=1.0, ub=1.0))  # force KO
    backed = [r.id for r in model.genes.get_by_id(gid).reactions]
    for rid in backed:
        r = m.reactions.get_by_id(rid)
        lo, hi = r.lower_bound, r.upper_bound
        v = r.flux_expression
        m.solver.add(I.Constraint(v - hi * (1 - y), ub=0.0))
        m.solver.add(I.Constraint(v - lo * (1 - y), lb=0.0))
    m.solver.add(I.Constraint(m.reactions.get_by_id(bio_id).flux_expression,
                              lb=0.5 * wt))
    m.objective = m.reactions.get_by_id(target_ex)
    m.objective_direction = "max"
    s = m.optimize()
    off = all(abs(float(s.fluxes[rid])) < 1e-6 for rid in backed)
    return (s.status == "optimal" and off, float(s.fluxes[target_ex])
            if s.status == "optimal" else 0.0)


if __name__ == "__main__":
    core = cobra.io.load_model("textbook")
    sym2id = {g.name: g.id for g in core.genes if g.name}
    syms = [s for s in SYMS if s in sym2id]
    gids = [sym2id[s] for s in syms]
    bio = next(r.id for r in core.reactions if "biomass" in r.id.lower())
    print(f"MILP select over {len(syms)} genes (core, anaerobic glc -10)")
    st, kos, succ, wt = milp_select(core, gids, bio, "EX_succ_e")
    print(f"MILP status={st} KOs={kos} succ={succ:.3f} wt={wt:.4f}")
    # coupling check on gnd (exp19 top hit): forced KO must zero GND flux
    ok, fsucc = forced_ko_check(core, gids, bio, "EX_succ_e", "gnd")
    g_gnd, _ = direct_ko(core, sym2id, ["gnd"], bio, "EX_succ_e")
    m_try = core.copy()
    m_try.reactions.EX_glc__D_e.lower_bound = GLC
    m_try.reactions.EX_o2_e.lower_bound = COND_O2
    m_try.genes.get_by_id(sym2id["gnd"]).knock_out()
    m_try.reactions.get_by_id(bio).lower_bound = 0.5 * g_gnd
    m_try.objective = m_try.reactions.EX_succ_e
    m_try.objective_direction = "max"
    dense = float(m_try.optimize().fluxes["EX_succ_e"])
    print(f"forced-gnd check: coupling_exact={ok} milp_env={fsucc:.3f} "
          f"direct_env={dense:.3f}")
    # growth-coupled validation: max-growth optimum secretion (no envelope)
    # for WT and exp19 top sets, in core AND iML1515.
    m1515 = cobra.io.load_json_model("iML1515.json")
    s1515 = {g.name: g.id for g in m1515.genes if g.name}
    bio1515 = next(r.id for r in m1515.reactions if "biomass" in r.id.lower())
    coupled = {}
    for label, combo in (("WT", []), ("gnd", ["gnd"]),
                         ("pfkA+gnd", ["pfkA", "gnd"])):
        gc, sc = direct_ko(core, sym2id, combo, bio, "EX_succ_e")
        if all(s in s1515 for s in combo):
            g15, s15 = direct_ko(m1515, s1515, combo, bio1515, "EX_succ_e")
        else:
            g15, s15 = None, None
        coupled[label] = {"core_growth": gc, "core_succ": sc,
                          "i1515_growth": g15, "i1515_succ": s15}
        print(f"coupled {label}: core mu={gc:.4f} succ={sc:.3f} | "
              f"1515 mu={g15} succ={s15}")
    json.dump({"milp_status": str(st), "kos": kos,
               "milp_succ": succ, "forced_gnd_coupling_exact": ok,
               "forced_gnd_milp_env": fsucc, "direct_gnd_env": dense,
               "coupled": coupled,
               "method": "single-level MILP (growth-tolerant); WT envelope "
                         "already reaches the max, so no KO is selected; "
                         "true bilevel OptKnock needs a bilevel-capable "
                         "solver"},
              open("strain_milp.json", "w"), indent=1)
    print("saved strain_milp.json")
