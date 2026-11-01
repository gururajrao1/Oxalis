# Oxalis

Experiments in constraint-based metabolic modeling of *E. coli* — aerobic vs
anaerobic growth, oxygen sweeps, genome-scale comparison, literature validation,
knockouts, sampling, batch dynamics, and substrate generality. Every number is
solved from a model with COBRApy; nothing is hand-drawn.

## Quickstart

```powershell
cd C:\Users\gurur\OneDrive\Documents\metabolism
uv run uvicorn server:app --port 8123
```

Then open **http://127.0.0.1:8123** in your browser. (Port 8000 is OS-reserved
on this machine, so 8123 is the address.)

Start in the app at **Guide: start here**. Every page ends with the command
that reproduces it. The full experiment log, bugfixes included, is `notes.md`.

## The idea in 60 seconds

Flux Balance Analysis (FBA) treats metabolism as a flow network. Reactions carry
flows (fluxes, mmol/gDW/h); at steady state each internal metabolite is produced
as fast as it is consumed. Given limits on food and oxygen, a solver finds the
flow pattern that maximizes growth. Growth rate (mu, 1/h) is the objective.

Two models: **core** ("textbook", 72 metabolites — fast, good for learning) and
**iML1515** (genome scale, 2712 reactions — realistic yields). Sign convention:
negative flux = uptake into the cell, positive = secretion.

## App pages

| Page | What it answers | Try this |
|---|---|---|
| Guide | What am I looking at? | Read first |
| Overview | Where are we? | Headline numbers per experiment |
| Aerobic vs anaerobic | Where does the carbon go? | Read the redox box |
| Carbon accounting | Can you close the balance? | Do the 4 checks, then reveal the Sankey |
| O2 sweep lab | Sharp kinks or smooth curve? | Drag the slider 0 → 25, flip core/iML1515 |
| Sampling | Point optimum or cloud? | Compare PFL anaerobic (tight) vs O2=14 (spread) |
| Batch culture | What happens over time? | Run O2 cap 5 vs 25, watch the acetate hump |
| Genome scale | Does the story survive iML1515? | Same trio, lower anaerobic yield |
| Network hubs | Which metabolites are hubs? | Toggle currency off, watch pyruvate surface |
| Literature anchor | Do we match real cells? | Growth within 5–20%; lactate missed |
| Knockouts | Which genes are essential? | Search `hemN`; compare FBA vs MOMA on `tpiA` |
| Gene deletions (core) | Teaching screen, 137 genes | Prediction check: 5 lethals on the boundary |
| pFBA & loops | Are flux paths unique? | pFBA picks the late-PFL path |
| Substrates | Does redox logic generalize? | Glycerol kills the acetate arm |
| Reproduce | Run everything | One command per experiment |

## Experiments (scripts → records)

| Script | Question | Headline |
|---|---|---|
| exp1 | Aerobic vs anaerobic carbon fate | CO2+biomass vs acetate/ethanol/formate thirds |
| exp2–4 | O2 sweep shape, kinks, degeneracy | Piecewise linear; PFL→PDH handoff; plateau at 22 |
| exp5 | iML1515 repeat | Same trio; anaerobic yield 0.212 → 0.158 |
| exp6 | Vs Varma & Palsson 1994 + product ratios | Growth 5–20%; trio right, lactate missed |
| exp7 | pFBA + loopless | Late-PFL path; FRD7/SUCDi loop harmless |
| exp8 | KO screen vs DEG essentials | 90% accuracy; hemN only anaerobic-specific |
| exp9 | Substrates + degree of reduction | Yield tracks redox; acetate can't ferment |
| exp10 | Sampling near-optimal states | Anaerobic point-like; O2=14 split roams |
| exp11 | dFBA batch dynamics | Overflow + diauxie; trio accumulation anaerobic |
| exp12 | FBA vs MOMA knockouts | tpiA aerobic: FBA viable, MOMA dead |
| exp13 | Network degree structure | h_c (35) tops; pyruvate (11) first real hub |
| exp14 | Core deletion screen | 5 lethal / 22 crippling / 9 mild / 101 none |
| exp15 | Carbon accounting + Sankey | PGI 48.6% vs oxPPP 49.6%; CO2 inventory closes |
| exp16 | Lactate tradeoff | 0 lac at optimum; 20.0 max at zero growth |
| exp17 | ATPM sweep | ~0.011 mu per ATPM; maintenance is only part of the gap |
| exp18 | dFBA + kLa gas transfer | Microaerobic spell; wider acetate hump |
| exp19 | Double-KO succinate scan | gnd-led sets ~9.35 potential; MOMA confirms |
| exp20 | Explicit biomass carbon | 42.56 C-mmol/gDW; gap 0.00 vs remainder |
| exp21 | 14.7-kink vectors | PFL->0 at 14.7; MDH switches on |

## Repo layout

- `server.py` — FastAPI backend: `/api/data/*` records, live solves, KO/MOMA, dFBA, `/api/dfba/kla`, `/api/biomass_carbon`
- `web/` — hand-built frontend, no frameworks (`index.html`, `styles.css`, `charts.js`, `app.js`)
- `exp*.py` — experiment scripts; each writes its CSV records + prints findings
- `*.csv` — precomputed records served by the app
- `*.png` — earlier matplotlib records (superseded in-app by SVG, kept as log)
- `iML1515.json` — genome-scale model (BiGG, fetched over https)
- `deg/` — Database of Essential Genes tables (knockout validation)
- `tests/test_api_data.py` — regression: every dataset must be strict-JSON clean
- `notes.md` — running lab log
- `.venv/` — project environment (COBRApy, FastAPI, pandas, matplotlib)

## Data sources & references

- Varma & Palsson 1994, AEM 60:3724–3731 (yields, uptakes, maintenance)
- J. Bacteriol. 182:620–626 (2000) (anaerobic product ratios)
- Baba et al. 2006 (Keio collection); DEG 15.0 (essential genes)
- Monk et al. 2017 (iML1515); Lewis et al. 2010 (pFBA)
- Mahadevan, Edwards & Doyle 2002 (dFBA); Segrè et al. 2002 (MOMA)

## Known limitations (honest list)

- Lactate tradeoff quantified (exp16): 0 at optimum, 20.0 max at zero growth; regulation still not modeled.
- iML1515 anaerobic gap split (exp17): maintenance explains part, costlier biomass the rest.
- dFBA now has a kLa gas-transfer path (exp18); Monod constants still plausible, not fitted.
- MOMA is linear only (no QP solver); strain scan is brute-force FBA+MOMA (exp19), true ROOM/OptKnock need MILP.
- DEG essentiality is rich-medium; the screen is glucose-minimal (hence biosynthesis "false positives" — correct on minimal).
