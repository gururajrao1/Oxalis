# Metabolism experiments — ugly v1 log

## Exp 1: aerobic vs anaerobic (textbook / e_coli_core, glucose -10)
- Aerobic mu = 0.874. Anaerobic (EX_o2_e LB=0) mu = 0.212.
- Anaerobic products: acetate 8.50, ethanol 8.28, formate 17.80. No lactate/succinate.
- Carbon: aerobic CO2 38% / biomass 62%; anaerobic etoh 27% / ac 28% / for 30% / biomass 15%.
- Files: exp1_aerobic_anaerobic.py, fluxes_*.csv, carbon_balance.csv, carbon_fate.png

## Exp 2: O2 sweep 0 -> 20 (step 0.5)
- PREDICTION (user, pre-registered): smooth saturation.
- RESULT: piecewise linear, concave, sharp kinks. Globally saturation-like, locally straight segments.
- Slopes (growth per O2): ~0.036 (0-6) -> ~0.0325 (6.5-14.5) -> ~0.023 (15-20).
- Kinks: ~6.3 ethanol hits 0; ~12 formate hits 0 (no growth-slope change); ~14.7 unidentified regime change (TODO: dump full flux vectors).
- At O2=20, mu=0.833, still rising; full aerobic (0.874) needs O2=21.8. Plateau outside swept range.
- Acetate first RISES (8.5 -> 13.2) as respiration frees acetyl-CoA from ethanol duty, then falls.
- Files: exp2_o2_sweep.py, o2_sweep.csv, o2_sweep.png

## Exp 3+4: plateau, kink ID, FVA
- Plateau: O2 stops binding at cap=22.0 (uptake 21.8, acetate -> 0 exactly there), mu=0.874 flat to 25.
- 14.7 kink NAMED: PFL -> PDH handoff completes. PFL/formate slope -> 0, PDH slope flips
  +2.06 -> -0.19, MDH switches on (TCA fully engaged), ATPS4r/NADH16 slopes drop.
- CORRECTION: exp2's "formate out at 12" was one arbitrary path through a degenerate region.
  Fresh-load O2=12 gives formate=6.5 (same growth 0.624); FVA at O2=14: formate 0-1.53,
  PDH 9.36-11.27 at identical growth. Robust claim: PFL off in ALL optima only at ~14.7.
  Growth values are solver-independent; flux paths in O2 12-14.7 are not.
- FVA anaerobic: fermentation mix UNIQUE (ac/etoh/for zero-width). Only slop: FRD7/SUCDi
  0-1000 loop (infeasible cycle artifact; loopless/pFBA removes it). Same loop at O2=14.
- Windows fixes: matplotlib Agg backend; FVA processes=1 (multiprocessing spawn re-runs script).
- Files: exp3_followups.py, exp4_fva_kink.py, o2_sweep25.*, kink_*.csv, fva_*.csv

## Exp 5: iML1515 genome-scale repeat (2712 rxns, glucose -10)
- Aerobic mu=0.8770 (core 0.8739); anaerobic mu=0.1575 (core 0.2117). Gap closes with O2.
- Anaerobic products: same trio (ac 8.83 / etoh 8.75 / for 18.23) + trace succinate 0.05
  at O2=0 only. No lactate anywhere. Core model's qualitative answer survives.
- Carbon: aerobic CO2 40% / biomass 60%; anaerobic trio ~29/29/30% + succ 0.35%, biomass 11%.
- Sweep: same piecewise-linear concave shape, ethanol out ~7, formate out ~14,
  saturates cap 22.5 (uptake 22.13). Curve sits slightly below core mid-range.
- Reading: costlier genome-scale biomass (higher ATP/g, ions/cofactors) bites hardest
  when ATP is scarce -> lower fermentative yield; negligible vs respiratory ATP.
- BUGFIX: carbon parser counted Cl/Ca/Cu/Co as carbon ('C' substring); now element-aware.
  Core results unaffected (no such metabolites); 1515 numbers above are post-fix.
- BiGG note: cobra load_model('iML1515') broken (http 301); fetched https JSON directly.
- Files: exp5_genome_scale.py, iML1515.json, fluxes_1515_*.csv, carbon_balance_1515.csv,
  carbon_fate_1515.png, o2_sweep_1515.png/csv

## Exp 6: anchor vs Varma&Palsson 1994 (W3110, measured uptakes)
- Aerobic (q_glc=10.5, o2cap=15): obs mu=0.68; core 0.738 (+8.5%), 1515 0.710 (+4.4%).
  Both predict acetate overflow (7.7 / 8.7) as observed. O2 cap is what tames FBA.
- Anaerobic (q_glc=18.5): obs mu=0.43; core 0.471 (+9%), 1515 0.342 (-20%).
  Core wins here: fixed maintenance (ATPM) dilutes at high uptake -> yield rises.
- Product ratios (per acetate): obs for:ac:etoh:lac=2.5:1:1:0.3;
  core 2.12:1:0.96:0, 1515 2.08:1:0.99:0. Trio nailed, lactate missed (regulation).
- Files: exp6_anchor.py, anchor_scorecard.csv, anchor.png

## Exp 7: pFBA + loopless (core + 1515)
- pFBA holds growth, same key fluxes; FRD7/SUCDi already 0 at vertices.
  Loopless verified on core anaerobic (mu unchanged, loop fluxes 0).
- pFBA sweep takes the LATE formate path (out at ~15), vs FBA-sequential early
  path (out at 12): parsimony resolves the degeneracy toward PFL-until-14.7.
- BUGFIX (mine): pfba().objective_value is the flux sum, not mu; read growth
  from a plain optimize. Fixed + rerun.
- Files: exp7_pfba.py, pfba_sweep.csv, pfba_compare.png

## Exp 8: KO screen vs DEG (Keio/PEC E. coli essential genes)
- 1515 aerobic: 196/1516 essential; anaerobic: 197/1516.
- vs DEG MG1655-II: acc=0.904, prec=0.41, rec=0.73. FP = arg/aro/bio/cys/his...
  (minimal-vs-rich medium mismatch, predicted behavior). FN incl. eno/fbaA/gapA/
  pgk (model finds unregulated bypasses) + non-metabolic (ligA, spoT...).
- ONLY anaerobic-specific essential: hemN (O2-independent coproporphyrinogen
  oxidase; hemF covers aerobically). No sick-only-anaerobic by 90%/50% cut.
- BUGFIX (mine): confusion-matrix off-diagonals were swapped in the plot; fixed.
- Files: exp8_knockouts.py, ko_1515_*.csv, ko_confusion.csv/png, deg/

## Exp 9+10: substrates + degree of reduction (iML1515, equal C uptake)
- Aerobic yield rises with DoR/C: glycerol(4.67) > glc=xyl(4.0) > ac(3.5) > suc=pyr(3.0).
  (DoR on model species at physiological protonation: acids deprotonated.)
- Anaerobic glycerol: NO acetate at all (64% etoh + 31% for C): excess electrons
  force everything into the NADH sink; growth collapses (no acetate ATP).
- Acetate/succinate anaerobic: mu=0 (nothing to ferment). Pyruvate anaerobic:
  63% acetate + 31% formate, no ethanol needed (substrate already oxidized).
- Files: exp9_substrates.py, substrates.csv/png

## App: Metabolism Lab workbench (FastAPI + hand-built UI, Benchling-style)
- Replaced the Streamlit app (removed app.py). No frameworks: vanilla JS + native SVG.
- 9 pages: Overview, Aerobic vs anaerobic, O2 sweep lab (live core/iML1515 solves +
  mini-sweep), Genome scale, Literature anchor, Knockouts (1515 lookup + live core
  KO), pFBA & loops, Substrates, Reproduce.
- API: /api/data/* (CSVs), /api/solve/point, /api/solve/sweep, /api/ko/live,
  /api/core_genes, /api/gene_names. All verified against known values.
- JS syntax-checked (node --check). BUGFIX (mine): anchor page compared CSV model
  "1515" as string vs parsed int; String() coercion.
- Infra: port 8000 sits in a Windows excluded range -> use 8123. Orphan watch:
  `uv run uvicorn` children survive session terminate; kill by verified cmdline.
- Run: `uv run uvicorn server:app --port 8123` -> http://127.0.0.1:8123
- Files: server.py, web/index.html, web/styles.css, web/charts.js, web/app.js

## Exp 10: sampling near-optimal states (core, OptGP, n=1000, >=95% opt)
- Anaerobic: PFL 17.2 +/- 0.3 (point-like optimum). O2=14: PFL 0.7 +/- 0.6
  (range 0-3.4), PDH 10.3 +/- 0.7 (7.5-13.1): split roams at identical growth.
- Files: exp10_sampling.py, sampling_o2_0.csv, sampling_o2_14.csv

## Exp 11: dFBA batch (core, Euler SOA, Monod bounds)
- Aerobic (glc 10mM, O2 cap 15): X 0.05->0.88, acetate humps to 7.3mM then
  re-eaten (diauxie); glc gone at t=3.75. Anaerobic: X->0.31, trio accumulates.
- Limits: O2 is a flux cap (no gas balance); Monod constants plausible, unfitted.
- Files: exp11_dfba.py (import-safe run_dfba*), dfba_aerobic.csv, dfba_anaerobic.csv

## Exp 12: FBA vs linear-MOMA KOs (core, 14 central genes x aer/ana)
- Showcase: tpiA aerobic FBA 0.704 viable vs MOMA 0.0 dead. pta/ackA covered by
  isozymes (full growth both methods). Anaerobic pgi/gapA/pgk/eno/ppc lethal both.
- BUGFIX (mine): slim_optimize returns NaN on infeasible KO -> record 0.0.
- Files: exp12_moma.py, moma_compare.csv

## App round 2: Guide/Sampling/Batch pages, MOMA block, README
- Bugfix: /api/data 500s (ko_anaerobic, anchor_scorecard): NaN survived
  DataFrame.where (None recasts to NaN in float cols). Fix: replace inf, astype
  (object), where notna -> None. Regression: tests/test_api_data.py (19 sets).
- Bugfix: ko_moma deadlocked (get_model locks internally; called inside _lock).
  Fix: acquire copies outside the lock. Audited all endpoints for nesting.
- Infra: never match own shell in kill filters (excluded 8000; kill by cmdline
  minus $PID). Orphan uvicorn workers outlive session terminate; verified kills.
- API add: /api/dfba/run, /api/ko/moma. UI add: Guide, Sampling, Batch culture,
  MOMA table + live tester. README.md with primer + page guide + honest limits.

## Exp 13: network degrees (72 mets, currency reasoned)
- Top: h_c 35, h2o_c 18, h_e 17 (bookkeeping); atp/nadh/pi/adp/nad 12-13
  (carriers); first pathway hub pyruvate 11, then co2 9, pep 8.
- Median/mean 3.0/5.00 with currency, 2.0/3.38 without. Judgment calls: CO2 kept
  (pathway carbon), CoA excluded (pure shuttle).
- Files: exp13_network.py, degrees.csv

## Exp 14: core KO screen (137 genes, prediction: lethal <5, result: exactly 5)
- Bins: lethal 5, crippling 22, mild 9, none 101. Lethals: gapA, pgk, eno
  (unbranched lower glycolysis), gltA (TCA entry), icd (sole 2-oxoglutarate
  route); each backs exactly one reaction in core.
- Files: exp14_core_ko.py, core_ko.csv

## Exp 15: carbon accounting (aerobic core, MODEL not measurement)
- G6P split: PGI 48.6% vs G6PDH2r 49.6% (NADPH demand). CO2: gross 25.31
  (PDH/ICDHyr/AKGDH/GND), PPC refixes 2.50, net 22.81 = EX_co2_e exactly.
- BUGFIX (mine): first version counted the CO2t export step as consumption
  (net 0.00); internal-only sum is the correct check.
- Files: exp15_carbon_accounting.py, carbon_accounting.json

## App round 3: Network/Deletions/Carbon pages (all four briefs clubbed in)
- API add: degrees, core_ko datasets; /api/carbon_accounting, /api/core_gene_info.
- UI add: currency-toggle hub chart, prediction-check deletion page, self-check
  accounting widgets + native SVG Sankey (downstream reconvergence flagged).

## Exp 16: lactate tradeoff (anaerobic core, glucose -10)
- WT optimum: growth 0.212, lactate 0.0 (acetate 8.50/ethanol 8.28/formate 17.80).
  Max lactate at >=90%/75%/50%/0% growth: 5.10/12.74/18.39/20.00.
- Reading: mixed-acid wins on ATP (acetate kinase) + NADH sink (ethanol); LDH
  only pays when growth is allowed to drop. Regulation invisible to FBA.
- Files: exp16_lactate.py, lactate_tradeoff.csv

## Exp 17: ATPM sweep (anaerobic, glucose -10, core vs iML1515)
- mu falls ~0.011 per ATPM unit in both models. Defaults: core 8.39, 1515 6.86.
- Lowering ATPM closes part of the anaerobic gap; the rest is costlier 1515
  biomass (ATP/g + cofactors), not maintenance alone.
- Files: exp17_maintenance.py, maintenance_sweep.csv

## Exp 18: dFBA with O2 gas transfer (kLa, core)
- Dissolved-O2 pool: dO2 = kLa*(O2star-O2) - qO2*X; uptake bound follows
  Monod in O2. kLa=inf recovers the old fixed-cap run.
- Default kLa=10: X 0.05->0.67, O2 bottoms out mid-batch, acetate hump lower
  and wider than fixed-cap (microaerobic spell).
- Files: exp18_kla.py (run_dfba_kla, import-safe), dfba_kla.csv;
  API: /api/dfba/kla

## Exp 19: strain-design demo (anaerobic core, 20 genes, 210 KO sets)
- Brute-force single+double KOs scored as max succinate at >=50% KO growth
  (pure-growth optimum secretes ~0, so optimum secretion finds nothing).
- Top envelope: gnd-led sets reach ~9.35 succinate potential; MOMA confirms the
  fresh-KO growth survives. True OptKnock/ROOM need a MILP solver (not shipped).
- Files: exp19_strain.py, strain_doubles.csv

## Exp 20: explicit biomass carbon (aerobic core, glucose -10)
- BUGFIX (mine): first version summed only substrate-side C (carriers counted,
  950 vs 37). Correct: net C = -sum(coeff*C) over the whole biomass equation
  (ATP/ADP, NAD(P)(H) cancel); biomass pseudo-met carries the residual.
- Result: 42.56 C-mmol/gDW x 0.8739 = 37.19 = remainder exactly. Gap = 0.00:
  the old shortcut is validated, now with proof.
- Files: exp20_biomass_c.py, biomass_carbon.json; API: /api/biomass_carbon

## Exp 21: 14.7-kink flux dump (closes the exp2 TODO)
- O2cap 12->16: PFL 6.52->0.00 by 14.7, PDH 5.23->10.60, MDH 0.00->0.06->0.98,
  formate tracks PFL to 0, acetate 8.73->5.81. TCA engages at the kink.
- Files: exp21_kink.py, kink_summary.csv, kink_vectors.csv

## Exp 22: kLa + Monod fit to a real batch curve (Enjalbert 2013, MG1655 M9)
- Targets: acetate peak 3.87 mM at GE (8.6% C), cleared ~3 h post-GE,
  X~1.16 gDW/L at GE (PMC3901295); mu 0.57 h-1 (feast-famine mSphere 2020).
- Fitted: vmax_glc=7.14, vmax_ac=0.96, o2cap=14.3 (cf V&P measured o2max=15),
  kLa>=200 lower bound (DOT>20%; fit used 400). Loss 0.011: peak 3.69,
  t_ac 2.95 h, mu 0.564, X_ge 1.26 (+9% residual = structural yield gap).
- Recovery test: optimizer refits synthetic features but params sit on a
  vmax_glc<->o2cap ridge (recovery [9.5,1.7,18] vs truth [8,2,15] at same
  loss) -> report fitted values as ridge ranges, not points.
- Files: exp22_kla_fit.py, kla_fit.json; API: /api/kla_fit

## Exp 18 bugfix (found by the fit): O2 pool Euler was unstable + uncapped
- Explicit update oscillated and clipped to phantom anaerobiosis for
  kLa*dt>1 (default kLa=10/dt=0.05 was borderline at 0.5); no o2star cap
  allowed supersaturation. Fix: semi-implicit update, clip [0,o2star],
  explicit kLa=inf branch recovers fixed-cap. Default trajectory unchanged
  in character (kLa=10 still goes microaerobic mid-batch).
- Starvation handling (opt-in scavenge=True, defaults bit-identical):
  max-growth LP goes INFEASIBLE when Monod-capped uptake cannot cover the
  forced ATPM floor (pools froze with food left, e.g. ac stuck at 0.16 mM);
  fallback is maintenance-first (max ATPM at LB 0, mu recorded 0) plus a
  lexicographic max-uptake pass when mu<0.05 (LP degeneracy leaves dregs).

## Exp 23: lactate regulation as imposed-bound cost accounting
- Observed anaerobic lactate (lac:ac=0.3, JB 182; anchored via Y=0.023 to
  3.76 mmol/g/h at q18.5) imposed: mu 0.4706->0.4550, cost 0.016 (3.3%).
- fnr-deletion mimic (PFL to 10%, FRD off): mu 0.4706->0.4300, 8.6% defect,
  directional match to reported anaerobic defect.
- arcA-deletion mimic (full oxidative arm ICDHyr/AKGDH/SUCDi/MDH to 1.5x):
  acetate 7.68->6.98 (9% cut, mu cost 0.016). ICDH alone bought only 3%:
  derepression bounds alone do NOT reproduce the full reported low-acetate
  phenotype -> needs global regulation beyond TCA bounds. All bounds imposed
  by hand; model contributes cost accounting only.
- Files: exp23_regulation.py, regulation_cost.csv (API: /api/data/regulation_cost)

## Exp 24: MILP knockout selection on an open solver (GLPK) + 1515 check
- Single-level MILP (binary KO vars, exact GPR OR-logic, big-M coupling,
  card<=2, growth floor 50%): verified machinery (forced-gnd KO zeroes GND,
  MILP envelope == direct envelope 9.352) and it selects NO knockouts —
  the WT envelope already reaches 9.352. Single-level max-product cannot
  distinguish KO strains from WT-at-reduced-growth: this is exactly why
  bilevel OptKnock is needed (still needs a bilevel-capable solver).
- Growth-coupled validation at max-growth optimum: core succinate 0.000
  (WT, gnd, pfkA+gnd); 1515 succinate 0.053 in ALL sets incl. WT (background
  reductive-branch trickle, not KO-induced; GND flux already 0 anaerobically
  so gnd KO is a no-op at the optimum). No growth-coupled succinate found.
- BUGFIXES (mine): optlang vars must come from model.solver.interface (not
  optlang.interface); MILP needs BOTH z+y<=1 and z+sum(y)>=1 links or z
  floats to 0 for free; cobra Solution must be checked via .status, never
  `== "optimal"`.
- Files: exp24_strain_milp.py, strain_milp.json; API: /api/strain_milp

## Exp 25: enzyme-constrained E. coli (eciML1515, GECKO) + protein cap
- Load: SysBioChalmers ecModels eciML1515.xml (10.9 MB SBML, 6084 rxns).
  BUGFIX (cobra): default SBML import applies F_REPLACE, which unescapes
  GECKO `__32__` (ascii-32) into real spaces -> optlang rejects the ids.
  Load with f_replace=None (raw R_/M_/G_ ids).
- Setup traps: GECKO splits reversibles into forward + _REV twins (uptake
  via _REV upper bounds); model ships with 100+ medium uptakes OPEN (mu
  74.9 on air) -> close all R_EX_*_REV except a mineral list; cobra
  auto-adds R_prot_*_exchange (0,1000) for boundary enzyme mets, so the
  shipped file is enzyme-unconstrained (reproduces iML1515 to 4 decimals).
- sMOMENT-lite cap: sum(flux*coeff*MW) <= P over 2560 enzyme arms, uniform
  MW 40 kDa. P<=0.15: mu 0.564 (= measured 0.57) with acetate overflow 11.5
  emerging purely from enzyme cost (plain FBA: ac=0). P<=0.2: mu 0.704,
  ac 5.9 (~V&P 0.68). Anaerobic q18.5 P<=0.15: mu 0.337, trio preserved.
  P<=0.05 over-constrains (mu 0.20, ac 17).
- PERF (mine): incremental sympy `sum()` over 6000 flux terms is O(n^2)
  (hung 15+ min); one Add(*terms) call builds it in seconds. Model loads
  once per process (10 MB parse ~2 min); sims reuse it via bound resets.
- Honest limits: uniform MW + fitted (not measured) P_total; per-enzyme
  MW/proteomics (Schmidt 2016) would pin both. Anaerobic P<=0.1 secretes
  lactate 12.5 (protein-efficient reshuffle; mechanism open).
- Files: exp25_econ.py, ec_compare.csv (API: /api/data/ec_compare);
  eciML1515.xml streams to temp cache on demand (round 5, not vendored)

## App round 5: API-first models (zero vendored weight)
- BiGG API streams iML1515 JSON (2.9 MB) to OS temp cache on first use;
  gene_names + genome solves use it. `git rm iML1515.json`; eciML1515.xml
  (10.4 MB) + web/vendor (0.8 MB) deleted from disk; Escher lib + map load
  from CDN at page-open. ~14 MB freed; temp cache evictable anytime.
- Verified: gene_names + core fluxes over live server; 29/29 datasets green.
- Files: server.py (cached_model_file), exp25_econ.py (ec_xml_path),
  web/app.js (ESCHER_CDN/MAP)

## App round 4: Flux map page (Escher) + /api/solve/fluxes
- Vendored escher.min.js 1.8.2 (self-contained UMD, d3 bundled) + BiGG
  e_coli_core map (95 rxns) under web/vendor/ (served by StaticFiles).
- UI: Flux map page (presets aerobic/anaerobic/V&P x2, optional core gene
  KO select, growth/status/drawn-reaction metrics) in a light viewport card
  inside the bench-dark theme. New /api/solve/fluxes (full BiGG-id vector;
  fresh model copy per request, KO-safe).
- Verified: node --check clean; endpoint payload strict-JSON; vendor + map
  HTTP 200 over a live server; anaerobic flux values correct. In-browser
  Escher render NOT exercised here (no browser on this machine) — open the
  Flux map page and press Draw map to confirm.
- Files: server.py (/api/solve/fluxes), web/app.js (pFluxmap), web/styles.css
  (#escher-box), web/vendor/

## TODO (next)
- Same-medium full time-course (OD/glc/ac at several time points) to turn
  the 4-feature fit into a real curve fit.
- Proteomics-backed bounds (e.g. Schmidt 2016) instead of hand-set
  regulation scenarios.
- Bilevel OptKnock with a bilevel-capable open solver (e.g. HiGHS/CBC
  bindings) for provably growth-coupled designs.
