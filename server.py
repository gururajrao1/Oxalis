"""Oxalis API + frontend.

Run from this folder:
    uv run uvicorn server:app --port 8000
Open:
    http://localhost:8000
"""
import json
import threading
from pathlib import Path

import cobra
import numpy as np
import pandas as pd
from cobra.flux_analysis import moma as moma_fn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from exp11_dfba import run_dfba, run_dfba_anaerobic
from exp18_kla import run_dfba_kla

ROOT = Path(__file__).parent
app = FastAPI(title="Oxalis", docs_url="/api/docs")
_lock = threading.Lock()
_models = {}


def get_model(name):
    if name not in ("core", "iML1515"):
        raise HTTPException(400, "model must be core or iML1515")
    with _lock:
        if name not in _models:
            _models[name] = (cobra.io.load_model("textbook") if name == "core"
                             else cobra.io.load_json_model(str(ROOT / "iML1515.json")))
        return _models[name].copy()


DATA_FILES = {
    "fluxes_aerobic": "fluxes_aerobic.csv",
    "fluxes_anaerobic": "fluxes_anaerobic.csv",
    "fluxes_1515_aerobic": "fluxes_1515_aerobic.csv",
    "fluxes_1515_anaerobic": "fluxes_1515_anaerobic.csv",
    "o2_sweep25": "o2_sweep25.csv",
    "o2_sweep_1515": "o2_sweep_1515.csv",
    "pfba_sweep": "pfba_sweep.csv",
    "anchor_scorecard": "anchor_scorecard.csv",
    "ko_confusion": "ko_confusion.csv",
    "ko_1515_aerobic": "ko_1515_aerobic.csv",
    "ko_1515_anaerobic": "ko_1515_anaerobic.csv",
    "substrates": "substrates.csv",
    "carbon_balance": "carbon_balance.csv",
    "carbon_balance_1515": "carbon_balance_1515.csv",
    "sampling_o2_0": "sampling_o2_0.csv",
    "sampling_o2_14": "sampling_o2_14.csv",
    "dfba_aerobic": "dfba_aerobic.csv",
    "dfba_anaerobic": "dfba_anaerobic.csv",
    "moma_compare": "moma_compare.csv",
    "degrees": "degrees.csv",
    "core_ko": "core_ko.csv",
    "lactate_tradeoff": "lactate_tradeoff.csv",
    "maintenance_sweep": "maintenance_sweep.csv",
    "dfba_kla": "dfba_kla.csv",
    "strain_doubles": "strain_doubles.csv",
    "kink_summary": "kink_summary.csv",
    "kink_vectors": "kink_vectors.csv",
}


@app.get("/api/carbon_accounting")
def carbon_accounting():
    return json.loads((ROOT / "carbon_accounting.json").read_text())


@app.get("/api/biomass_carbon")
def biomass_carbon():
    return json.loads((ROOT / "biomass_carbon.json").read_text())


@app.get("/api/core_gene_info")
def core_gene_info():
    m = get_model("core")
    return {g.id: {"name": g.name or g.id,
                   "reactions": [{"id": r.id, "name": r.name} for r in g.reactions]}
            for g in m.genes}


@app.get("/api/data/{name}")
def data(name):
    if name not in DATA_FILES:
        raise HTTPException(404, "unknown dataset")
    df = pd.read_csv(ROOT / DATA_FILES[name])
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.astype(object).where(df.notna(), None)  # object dtype keeps None as None
    return {"columns": list(df.columns), "rows": df.to_dict("records")}


@app.get("/api/growth_comparison")
def growth_comparison():
    return {"core": {"aerobic": 0.8739, "anaerobic": 0.2117},
            "iML1515": {"aerobic": 0.8770, "anaerobic": 0.1575}}


def _point(model, o2max, glc):
    m = get_model(model)
    with _lock:
        m.reactions.EX_glc__D_e.lower_bound = -glc
        m.reactions.EX_o2_e.lower_bound = -o2max
        s = m.optimize()
        f = s.fluxes
        grab = ["EX_ac_e", "EX_etoh_e", "EX_for_e", "EX_lac__D_e",
                "EX_succ_e", "EX_co2_e", "EX_o2_e", "EX_glc__D_e"]
        return {"growth": float(s.objective_value), "status": s.status,
                "fluxes": {r: float(f[r]) for r in grab if r in f}}


@app.get("/api/solve/point")
def solve_point(model: str = "core", o2max: float = 10.0, glc: float = 10.0):
    return _point(model, o2max, glc)


@app.get("/api/solve/sweep")
def solve_sweep(model: str = "core", o2max: float = 25.0, step: float = 1.0):
    m = get_model(model)
    out = []
    with _lock:
        o = 0.0
        while o <= o2max + 1e-9:
            m.reactions.EX_o2_e.lower_bound = -o
            s = m.optimize()
            f = s.fluxes
            out.append({"o2": round(o, 2), "growth": float(s.objective_value),
                        "ac": float(f["EX_ac_e"]), "etoh": float(f["EX_etoh_e"]),
                        "for": float(f["EX_for_e"])})
            o += step
    return out


@app.get("/api/core_genes")
def core_genes():
    return sorted(get_model("core").genes.list_attr("id"))


@app.get("/api/ko/live")
def ko_live(gene: str, model: str = "core"):
    m = get_model(model)
    with _lock:
        try:
            m.genes.get_by_id(gene).knock_out()
        except KeyError:
            raise HTTPException(404, f"no such gene: {gene}")
        aer = float(m.slim_optimize())
        m.reactions.EX_o2_e.lower_bound = 0
        ana = float(m.slim_optimize())
    return {"gene": gene, "aerobic": aer, "anaerobic": ana}


@app.get("/api/gene_names")
def gene_names():
    d = json.loads((ROOT / "iML1515.json").read_text())
    return {g["id"]: (g.get("name") or g["id"]) for g in d["genes"]}


@app.get("/api/dfba/run")
def dfba_run(o2cap: float = 15.0, glc0: float = 10.0, dt: float = 0.05,
             T: float = 14.0, anaerobic: bool = False):
    if not (0.02 <= dt <= 1.0) or not (1.0 <= T <= 30.0) or T / dt > 1500:
        raise HTTPException(400, "step grid too fine or horizon out of range")
    if anaerobic:
        return run_dfba_anaerobic(glc0=glc0, dt=dt, T=T)
    return run_dfba(o2cap=o2cap, glc0=glc0, dt=dt, T=T)


@app.get("/api/dfba/kla")
def dfba_kla(o2cap: float = 15.0, glc0: float = 10.0, dt: float = 0.05,
             T: float = 14.0, kla: float = 10.0, o2star: float = 0.2):
    if not (0.02 <= dt <= 1.0) or not (1.0 <= T <= 30.0) or T / dt > 1500:
        raise HTTPException(400, "step grid too fine or horizon out of range")
    return run_dfba_kla(o2cap=o2cap, glc0=glc0, dt=dt, T=T, kla=kla, o2star=o2star)


@app.get("/api/ko/moma")
def ko_moma(gene: str, model: str = "core", cond: str = "aerobic"):
    o2 = 0.0 if cond == "anaerobic" else -1000.0
    w = get_model(model)  # outside _lock: get_model locks internally (non-reentrant)
    m = get_model(model)
    with _lock:
        w.reactions.EX_glc__D_e.lower_bound = -10.0
        w.reactions.EX_o2_e.lower_bound = o2
        wt_sol = w.optimize()
        wt_g = float(wt_sol.objective_value)
        try:
            m.genes.get_by_id(gene)
            gid = gene
        except KeyError:
            match = [g.id for g in m.genes if (g.name or "").lower() == gene.lower()]
            if not match:
                raise HTTPException(404, f"no such gene: {gene}")
            gid = match[0]
        m.reactions.EX_glc__D_e.lower_bound = -10.0
        m.reactions.EX_o2_e.lower_bound = o2
        m.genes.get_by_id(gid).knock_out()
        ks = m.optimize()
        fba_g = float(ks.objective_value) if ks.status == "optimal" else 0.0
        bio = next(r.id for r in m.reactions if "biomass" in r.id.lower())
        try:
            ms = moma_fn(m, solution=wt_sol, linear=True)
            moma_g = float(ms.fluxes[bio]) if ms.status == "optimal" else 0.0
        except Exception:
            moma_g = None
    return {"gene": gid, "cond": cond, "wt": wt_g, "fba": fba_g, "moma": moma_g}


app.mount("/", StaticFiles(directory=str(ROOT / "web"), html=True), name="web")
