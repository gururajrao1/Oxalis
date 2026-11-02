/* Oxalis pages. Data: precomputed CSVs via /api/data/*, live solves via /api/solve/*. */
const NAV = [
  ["sec", "Workbench"],
  ["guide", "Guide: start here"],
  ["overview", "Overview"],
  ["aerana", "Aerobic vs anaerobic"],
  ["carbon", "Carbon accounting"],
  ["o2lab", "O2 sweep lab"],
  ["sampling", "Sampling"],
  ["dfba", "Batch culture"],
  ["fluxmap", "Flux map"],
  ["genome", "Genome scale"],
  ["network", "Network hubs"],
  ["sec", "Validation"],
  ["anchor", "Literature anchor"],
  ["ko", "Knockouts"],
  ["deletions", "Gene deletions (core)"],
  ["pfba", "pFBA & loops"],
  ["subs", "Substrates"],
  ["sec", "Project"],
  ["repro", "Reproduce"],
];

async function api(path, init) {
  const r = await fetch(path, init);
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}

// Long runs with live progress, elapsed timer, and click-to-cancel.
function longRun(btn, out, fn) {
  let ctl = null;
  btn.addEventListener("click", async () => {
    if (ctl) { ctl.abort(); return; }
    ctl = new AbortController();
    const sig = ctl.signal;
    if (!btn.dataset.idle) btn.dataset.idle = btn.textContent;
    btn.textContent = "Cancel";
    const t0 = performance.now();
    out.innerHTML = `<div class="progress"><i></i></div><div class="runstat">running… click Cancel to stop</div>`;
    const stat = out.querySelector(".runstat");
    const tick = setInterval(() => {
      if (stat.isConnected) stat.textContent = `running ${((performance.now() - t0) / 1000).toFixed(1)} s — click Cancel to stop`;
    }, 200);
    try {
      await fn(sig);
      if (out.querySelector(".progress")) out.innerHTML = "";
      else { out.classList.remove("fadein"); void out.offsetWidth; out.classList.add("fadein"); }
    } catch (e) {
      if (e && e.name === "AbortError") out.innerHTML = `<p class="muted">Cancelled.</p>`;
      else out.innerHTML = `<p class="err">${esc(e.message)}</p>`;
    } finally {
      clearInterval(tick);
      if (btn.isConnected) btn.textContent = btn.dataset.idle;
      ctl = null;
    }
  });
}
const head = (t, s) => `<div class="pagehead"><h1>${t}</h1><p>${s}</p></div>`;
const card = (t, inner) => `<div class="card"><h2>${t}</h2>${inner}</div>`;
const cmd = t => `<pre class="cmd">${esc(t)}</pre>`;
const FLUX_COLS = [["reaction", "Exchange"], ["formula", "Formula"], ["C", "C"], ["flux", "Flux"]];
const PROD_NAMES = { EX_ac_e: "acetate", EX_etoh_e: "ethanol", EX_for_e: "formate", EX_lac__D_e: "lactate", EX_succ_e: "succinate", EX_co2_e: "CO2", EX_pyr_e: "pyruvate", EX_meoh_e: "methanol" };

function carbonFate(rows, groupMinor) {
  let up = 0;
  const secs = [];
  for (const r of rows) {
    const cf = r.flux * r.C;
    if (cf < -1e-9) up -= cf;
    else if (cf > 1e-9) secs.push({ id: r.reaction, v: cf });
  }
  let segs = secs.map(s => ({ name: PROD_NAMES[s.id] || s.id, value: 100 * s.v / up }));
  if (groupMinor) {
    const major = segs.filter(s => s.value >= 1);
    const minor = segs.filter(s => s.value < 1).reduce((a, s) => a + s.value, 0);
    segs = major;
    if (minor > 0) segs.push({ name: "other", value: minor });
  }
  segs.push({ name: "biomass", value: 100 - segs.reduce((a, s) => a + s.value, 0) });
  segs.forEach(s => { s.color = PRODUCT_COLORS[s.name] || PAL.steel; });
  return { uptake: up, segments: segs };
}
const ORDER = ["acetate", "ethanol", "formate", "lactate", "succinate", "pyruvate", "CO2", "methanol", "other", "biomass"];
const sortSegs = segs => segs.sort((a, b) => ORDER.indexOf(a.name) - ORDER.indexOf(b.name));

async function pOverview(v) {
  const g = await api("/api/growth_comparison");
  v.innerHTML = head("Overview", "Aerobic vs anaerobic metabolism as experiments. Pick a page on the left; live pages solve COBRApy on demand.") +
    `<div class="metrics" style="margin-bottom:16px">
      <div class="metric"><div class="l">Core aerobic / anaerobic</div><div class="v">${g.core.aerobic} / ${g.core.anaerobic}</div><div class="d muted">growth /h, glucose -10</div></div>
      <div class="metric"><div class="l">iML1515 aerobic / anaerobic</div><div class="v">${g.iML1515.aerobic} / ${g.iML1515.anaerobic}</div><div class="d muted">growth /h, glucose -10</div></div>
      <div class="metric"><div class="l">KO accuracy vs DEG</div><div class="v">0.90</div><div class="d muted">1516 genes, MG1655-II</div></div>
      <div class="metric"><div class="l">Anchor error</div><div class="v">4-20%</div><div class="d muted">vs Varma &amp; Palsson 1994</div></div>
    </div>` +
    card("Experiments", dataTable(
      [["n", ""], ["q", "Question"], ["h", "Headline"], ["s", "Script"]],
      [
        { n: "1", q: "Where does the carbon go?", h: "Aerobic: CO2 + biomass. Anaerobic: acetate/ethanol/formate thirds.", s: "exp1" },
        { n: "2", q: "Sharp kinks or smooth saturation?", h: "Piecewise linear; ethanol-out, PFL->PDH handoff, plateau at 22.", s: "exp2-4" },
        { n: "3", q: "Does the story survive iML1515?", h: "Yes qualitatively; anaerobic yield 0.212 -> 0.158.", s: "exp5" },
        { n: "4", q: "Do numbers match real E. coli?", h: "Growth within 5-20%; trio right, lactate missed.", s: "exp6" },
        { n: "5", q: "Which genes are essential?", h: "90% vs DEG; hemN is the only anaerobic-specific essential.", s: "exp8" },
        { n: "6", q: "Are flux paths unique?", h: "pFBA picks late-PFL path; FRD7/SUCDi loop is harmless.", s: "exp7" },
        { n: "7", q: "Does redox logic generalize?", h: "Yield tracks degree of reduction; glycerol kills acetate arm.", s: "exp9" },
      ])) +
    card("How to use this tool", `<p>Each page shows the result, the data behind it, and the rerun command. Pages marked live solve the model in this session: drag the O2 slider, run a sweep, or knock out a gene. The <b>Reproduce</b> page reruns every experiment from a shell. Full log with bugfixes: <code class="inline">notes.md</code>.</p>`);
}

async function pAerana(v) {
  const [aer, ana] = await Promise.all([api("/api/data/fluxes_aerobic"), api("/api/data/fluxes_anaerobic")]);
  const fa = carbonFate(aer.rows), fn = carbonFate(ana.rows);
  sortSegs(fa.segments); sortSegs(fn.segments);
  v.innerHTML = head("Aerobic vs anaerobic", "Core model, glucose uptake -10. Flux units mmol/gDW/h; negative is uptake.") +
    `<div class="metrics" style="margin-bottom:16px">
      <div class="metric"><div class="l">Aerobic growth</div><div class="v">0.874</div><div class="d muted">O2 uptake 21.8</div></div>
      <div class="metric"><div class="l">Anaerobic growth</div><div class="v">0.212</div><div class="d down">-76% vs aerobic</div></div>
      <div class="metric"><div class="l">Anaerobic carbon to biomass</div><div class="v">14.9%</div><div class="d muted">vs 62.0% aerobic</div></div>
    </div>
    <div class="grid2">` +
    card("Carbon fate (% of carbon taken up)", stackedBars({
      categories: [{ label: "aerobic", segments: fa.segments }, { label: "anaerobic", segments: fn.segments }],
      ylabel: "% of carbon taken up"
    })) +
    card("Why these products (redox)", `<p>Glycolysis makes NADH that must be reoxidized. Aerobically the respiratory chain dumps it onto O2. Without O2, pyruvate splits via PFL into formate + acetyl-CoA; half the acetyl-CoA goes to <b>acetate</b> (+1 ATP, no NADH use) and half to <b>ethanol</b> (uses 2 NADH, no ATP). The ~1:1 split is the redox-balanced, ATP-maximizing compromise.</p><p class="muted">Yield cannot be recovered by growing slower: biomass costs fixed ATP per gram, and fermentation gives ~2-3 ATP per glucose against far more with respiration.</p>`) +
    `</div><div class="grid2">` +
    card("Aerobic exchanges", dataTable(FLUX_COLS, aer.rows, { num: [0, 0, 0, 1], dec: [0, 0, 0, 2] })) +
    card("Anaerobic exchanges", dataTable(FLUX_COLS, ana.rows, { num: [0, 0, 0, 1], dec: [0, 0, 0, 2] })) +
    `</div>` + card("Rerun", cmd("uv run python exp1_aerobic_anaerobic.py"));
}

async function pO2lab(v) {
  const rec = await api("/api/data/o2_sweep25");
  const pts = c => rec.rows.map(r => [r.o2_max, r[c]]);
  v.innerHTML = head("O2 sweep lab", "Precomputed record plus live solves. Growth is piecewise linear; each kink is a pathway switching off.") +
    card("Record: growth and secretions across O2 (core)", lineChart({
      series: [{ name: "growth", color: PAL.blue, points: pts("growth") }], ylabel: "growth (1/h)"
    }) + lineChart({
      series: [
        { name: "acetate", color: PRODUCT_COLORS.acetate, points: pts("ac") },
        { name: "ethanol", color: PRODUCT_COLORS.ethanol, points: pts("etoh") },
        { name: "formate", color: PRODUCT_COLORS.formate, points: pts("for") },
      ], ylabel: "secretion flux"
    })) +
    card("Solve live", `
      <label class="field">Model</label>
      <select id="o2model"><option value="core">core (fast)</option><option value="iML1515">iML1515 (slow)</option></select>
      <label class="field">Max O2 uptake: <span id="o2val">10.0</span> mmol/gDW/h</label>
      <input type="range" id="o2slider" min="0" max="25" step="0.5" value="10">
      <div class="metrics" style="margin-top:12px">
        <div class="metric"><div class="l">Growth</div><div class="v" id="mGrowth">-</div></div>
        <div class="metric"><div class="l">Acetate</div><div class="v" id="mAc">-</div></div>
        <div class="metric"><div class="l">Ethanol</div><div class="v" id="mEt">-</div></div>
        <div class="metric"><div class="l">Formate</div><div class="v" id="mFo">-</div></div>
      </div>
      <button class="btn primary" id="sweepBtn">Run live sweep 0-25</button>
      <div id="sweepOut" style="margin-top:12px"></div>`);
  const slider = document.getElementById("o2slider");
  const cells = ["mGrowth", "mAc", "mEt", "mFo"].map(id => document.getElementById(id));
  let solveSeq = 0, solveCtl = null;
  const solve = async () => {
    const my = ++solveSeq;
    const o2 = parseFloat(slider.value);
    document.getElementById("o2val").textContent = o2.toFixed(1);
    const model = document.getElementById("o2model").value;
    if (solveCtl) solveCtl.abort();
    solveCtl = new AbortController();
    const sig = solveCtl.signal;
    cells.forEach(el => el.classList.add("pending"));
    try {
      const r = await api(`/api/solve/point?model=${model}&o2max=${o2}&glc=10`, { signal: sig });
      if (my !== solveSeq || sig.aborted) return;
      document.getElementById("mGrowth").textContent = fmt(r.growth, 3);
      document.getElementById("mAc").textContent = fmt(r.fluxes.EX_ac_e, 2);
      document.getElementById("mEt").textContent = fmt(r.fluxes.EX_etoh_e, 2);
      document.getElementById("mFo").textContent = fmt(r.fluxes.EX_for_e, 2);
    } catch (e) {
      if (my === solveSeq && (!e || e.name !== "AbortError")) document.getElementById("mGrowth").textContent = "err";
    } finally {
      if (my === solveSeq) cells.forEach(el => el.classList.remove("pending"));
    }
  };
  let t;
  slider.addEventListener("input", () => { clearTimeout(t); t = setTimeout(solve, 70); });
  document.getElementById("o2model").addEventListener("change", solve);
  solve();
  longRun(document.getElementById("sweepBtn"), document.getElementById("sweepOut"), async (sig) => {
    const model = document.getElementById("o2model").value;
    const rows = await api(`/api/solve/sweep?model=${model}&o2max=25&step=1`, { signal: sig });
    if (sig.aborted) return;
    document.getElementById("sweepOut").innerHTML = lineChart({
      series: [{ name: `growth (${model}, live)`, color: PAL.blue, points: rows.map(r => [r.o2, r.growth]) }],
      ylabel: "growth (1/h)"
    });
  });
}

async function pGenome(v) {
  const [aer, ana, sw15, swc] = await Promise.all([
    api("/api/data/fluxes_1515_aerobic"), api("/api/data/fluxes_1515_anaerobic"),
    api("/api/data/o2_sweep_1515"), api("/api/data/o2_sweep25")]);
  const fa = carbonFate(aer.rows, true), fn = carbonFate(ana.rows, true);
  sortSegs(fa.segments); sortSegs(fn.segments);
  v.innerHTML = head("Genome scale", "iML1515 (2712 reactions) repeats the core experiments. Same trio, same curve shape, costlier biomass.") +
    `<div class="metrics" style="margin-bottom:16px">
      <div class="metric"><div class="l">Aerobic mu</div><div class="v">0.877</div><div class="d muted">core 0.874</div></div>
      <div class="metric"><div class="l">Anaerobic mu</div><div class="v">0.158</div><div class="d down">core 0.212</div></div>
      <div class="metric"><div class="l">Anaerobic C to biomass</div><div class="v">10.8%</div><div class="d muted">core 14.9%</div></div>
      <div class="metric"><div class="l">O2 for full aerobe</div><div class="v">22.5</div><div class="d muted">uptake 22.1</div></div>
    </div>
    <div class="grid2">` +
    card("Carbon fate, iML1515", stackedBars({
      categories: [{ label: "aerobic", segments: fa.segments }, { label: "anaerobic", segments: fn.segments }],
      ylabel: "% of carbon taken up"
    })) +
    card("Growth vs O2: iML1515 vs core", lineChart({
      series: [
        { name: "iML1515", color: PAL.blue, points: sw15.rows.map(r => [r.o2_max, r.growth]) },
        { name: "core", color: PAL.amber, points: swc.rows.map(r => [r.o2_max, r.growth]), dash: "5 3" },
      ], ylabel: "growth (1/h)"
    })) +
    `</div>` + card("Reading", `<p class="muted">Costlier genome-scale biomass (more ATP per gram, ions, cofactors) bites hardest when ATP is scarcest, so fermentative yield drops while aerobic growth is unchanged. No lactate anywhere; a trace of succinate appears only at O2 = 0.</p>`) +
    card("Rerun", cmd("uv run python exp5_genome_scale.py"));
}

async function pAnchor(v) {
  const sc = await api("/api/data/anchor_scorecard");
  const get = (m, k) => sc.rows.find(r => String(r.model) === m && r.metric === k).predicted;
  v.innerHTML = head("Literature anchor", "Model vs measured E. coli W3110 at the paper's own uptake rates (Varma & Palsson 1994).") +
    `<div class="grid2">` +
    card("Growth at measured uptakes", groupedBars({
      labels: ["aerobic mu", "anaerobic mu"],
      series: [
        { name: "observed", color: PAL.slate, values: [0.68, 0.43] },
        { name: "core", color: PAL.blue, values: [get("core", "aer_mu"), get("core", "ana_mu")] },
        { name: "iML1515", color: PAL.teal, values: [get("1515", "aer_mu"), get("1515", "ana_mu")] },
      ], ylabel: "growth (1/h)"
    })) +
    card("Anaerobic product ratios (per acetate)", groupedBars({
      labels: ["formate", "acetate", "ethanol", "lactate"],
      series: [
        { name: "observed", color: PAL.slate, values: [2.5, 1.0, 1.0, 0.3] },
        { name: "core", color: PAL.blue, values: [get("core", "y_for") / get("core", "y_ac"), 1, get("core", "y_etoh") / get("core", "y_ac"), 0] },
        { name: "iML1515", color: PAL.teal, values: [get("1515", "y_for") / get("1515", "y_ac"), 1, get("1515", "y_etoh") / get("1515", "y_ac"), 0] },
      ], ylabel: "mol / mol acetate"
    })) +
    `</div>` +
    card("Scorecard", dataTable(
      [["model", "Model"], ["metric", "Metric"], ["predicted", "Predicted"], ["observed", "Observed"], ["err_pct", "Err %"]],
      sc.rows.filter(r => r.observed !== null),
      { num: [0, 0, 1, 1, 1], dec: [0, 0, 4, 4, 1] })) +
    card("What matches, what doesn't", `<ul><li>Aerobic at measured uptakes (glc 10.5, O2 cap 15): 1515 within 4.4%, core within 8.5%. Both predict the observed acetate overflow. The O2 cap is what tames FBA.</li><li>Anaerobic at q_glc 18.5: core within 9% because fixed ATP maintenance dilutes at high uptake; 1515 underpredicts by 20%.</li><li>Ratios: trio nailed, lactate missed (0 vs 0.3) - regulation the model doesn't know about.</li></ul><p class="muted">Sources: Varma &amp; Palsson 1994 (growth/yields); J. Bacteriol. 182:620-626 (ratios).</p>`) +
    card("Rerun", cmd("uv run python exp6_anchor.py"));
}

function koId(x) { const m = String(x).match(/[bs]\d+/); return m ? m[0] : String(x); }

async function pKO(v) {
  const [cf, aer, ana, names, mc] = await Promise.all([
    api("/api/data/ko_confusion"), api("/api/data/ko_1515_aerobic"),
    api("/api/data/ko_1515_anaerobic"), api("/api/gene_names"),
    api("/api/data/moma_compare")]);
  const m2 = cf.rows.find(r => r.set === "Escherichia coli MG1655 II");
  const am = {}, nm = {};
  aer.rows.forEach(r => { am[koId(r.ids)] = r; });
  ana.rows.forEach(r => { nm[koId(r.ids)] = r; });
  v.innerHTML = head("Knockouts", "Single-gene deletions on iML1515, aerobic + anaerobic, vs DEG essential genes.") +
    `<div class="grid2">` +
    card(`Essentiality vs DEG MG1655-II (acc ${fmt(m2.acc, 2)})`, confusion({
      matrix: [[m2.TP, m2.FN], [m2.FP, m2.TN]], cols: ["pred ess", "pred viable"], rows: ["DEG ess", "DEG viable"]
    }) + `<p class="muted">TP ${m2.TP} · FN ${m2.FN} · FP ${m2.FP} · TN ${m2.TN}. False positives are arg/aro/bio/cys/his biosynthesis: essential on minimal medium (screen), viable on rich (DEG) - the predicted pattern. The only anaerobic-specific essential is <b>hemN</b>.</p>`) +
    card("Look up a gene", `
      <label class="field">Gene (b-number or name)</label>
      <input type="text" id="koq" value="hemN">
      <div id="kohit" style="margin-top:10px"></div>`) +
    `</div>` +
    card("Live KO tester (core model)", `
      <label class="field">Gene</label><select id="kosel"></select>
      <div class="metrics" style="margin-top:12px">
        <div class="metric"><div class="l">KO aerobic</div><div class="v" id="koA">-</div></div>
        <div class="metric"><div class="l">KO anaerobic</div><div class="v" id="koN">-</div></div>
      </div>`) +
    card("FBA vs MOMA: adapted strain vs fresh knockout", `<p class="muted">FBA re-optimizes the mutant (adapted). MOMA stays closest to the wild-type flux state (fresh knockout). They disagree where rewiring is expensive - tpiA aerobically is the showcase. pta/ackA stay viable: isozymes cover them.</p>` + dataTable(
      [["sym", "Gene"], ["cond", "Cond"], ["wt", "WT"], ["fba", "FBA"], ["moma", "MOMA"], ["call", "Call"]],
      mc.rows.map(r => {
        const alive = g => g > 0.05 * r.wt;
        return { sym: r.sym, cond: r.cond, wt: r.wt, fba: r.fba, moma: r.moma, call: alive(r.fba) === alive(r.moma) ? (alive(r.fba) ? "agree viable" : "agree lethal") : "DISAGREE" };
      }),
      { num: [0, 0, 1, 1, 1, 0], dec: [0, 0, 3, 3, 3, 0], scroll: 300 })) +
    card("Live FBA-vs-MOMA tester (core)", `
      <label class="field">Gene (b-number or symbol)</label><input type="text" id="mmq" value="tpiA">
      <label class="field">Condition</label><select id="mmc"><option value="aerobic">aerobic</option><option value="anaerobic">anaerobic</option></select>
      <div><button class="btn primary" id="mmb">Compare</button></div><div class="runstat" id="mmS"></div>
      <div class="metrics" style="margin-top:12px">
        <div class="metric"><div class="l">FBA</div><div class="v" id="mmF">-</div></div>
        <div class="metric"><div class="l">MOMA</div><div class="v" id="mmM">-</div></div>
        <div class="metric"><div class="l">Verdict</div><div class="v" id="mmV" style="font-size:15px">-</div></div>
      </div>`) +
    card("Rerun", cmd("uv run python exp8_knockouts.py  # screen\nuv run python exp12_moma.py      # FBA vs MOMA"));
  const render = () => {
    const q = document.getElementById("koq").value.trim().toLowerCase();
    const gid = Object.keys(am).find(g => g.toLowerCase() === q) ||
      Object.keys(am).find(g => (names[g] || "").toLowerCase() === q);
    const el = document.getElementById("kohit");
    if (!gid) { el.innerHTML = `<p class="err">Not in screen. Try hemN, pflB, gapA, b3867.</p>`; return; }
    const a = am[gid], n = nm[gid];
    el.innerHTML = `<p><b>${gid}</b> (${esc(names[gid] || gid)})</p>` + dataTable(
      [["c", "Condition"], ["g", "Growth"], ["f", "Fraction"], ["e", "Call"]],
      [{ c: "aerobic", g: a.growth, f: a.frac, e: a.essential ? "essential" : "viable" },
       { c: "anaerobic", g: n.growth, f: n.frac, e: n.essential ? "essential" : "viable" }],
      { num: [0, 1, 1, 0], dec: [0, 4, 3, 0] });
  };
  document.getElementById("koq").addEventListener("input", render);
  render();
  const genes = await api("/api/core_genes");
  const sel = document.getElementById("kosel");
  sel.innerHTML = genes.map(g => `<option>${g}</option>`).join("");
  let koSeq = 0, koCtl = null;
  const live = async () => {
    const my = ++koSeq;
    if (koCtl) koCtl.abort();
    koCtl = new AbortController();
    const sig = koCtl.signal;
    const a = document.getElementById("koA"), n = document.getElementById("koN");
    a.classList.add("pending"); n.classList.add("pending");
    try {
      const r = await api(`/api/ko/live?gene=${sel.value}&model=core`, { signal: sig });
      if (my !== koSeq || sig.aborted) return;
      a.textContent = fmt(r.aerobic, 3);
      n.textContent = fmt(r.anaerobic, 3);
    } catch (e) {
      if (my === koSeq && (!e || e.name !== "AbortError")) a.textContent = "err";
    } finally {
      if (my === koSeq) { a.classList.remove("pending"); n.classList.remove("pending"); }
    }
  };
  sel.addEventListener("change", live);
  live();
  longRun(document.getElementById("mmb"), document.getElementById("mmS"), async (sig) => {
    const r = await api(`/api/ko/moma?gene=${encodeURIComponent(document.getElementById("mmq").value.trim())}&model=core&cond=${document.getElementById("mmc").value}`, { signal: sig });
    if (sig.aborted) return;
    document.getElementById("mmF").textContent = fmt(r.fba, 3);
    document.getElementById("mmM").textContent = r.moma === null ? "n/a" : fmt(r.moma, 3);
    const alive = g => g !== null && g > 0.05 * r.wt;
    document.getElementById("mmV").textContent =
      alive(r.fba) === alive(r.moma) ? (alive(r.fba) ? "agree viable" : "agree lethal") : "DISAGREE";
  });
}

async function pPfba(v) {
  const [pf, fb] = await Promise.all([api("/api/data/pfba_sweep"), api("/api/data/o2_sweep25")]);
  v.innerHTML = head("pFBA & loops", "Parsimony resolves the degenerate O2 12-15 window; the FRD7/SUCDi cycle is verified harmless.") +
    card("Growth: pFBA vs FBA (identical by construction)", lineChart({
      series: [
        { name: "pFBA", color: PAL.blue, points: pf.rows.map(r => [r.o2_max, r.growth]) },
        { name: "FBA", color: PAL.amber, points: fb.rows.map(r => [r.o2_max, r.growth]), dash: "5 3" },
      ], ylabel: "growth (1/h)"
    })) +
    card("Formate path: pFBA picks late-PFL shutdown", lineChart({
      series: [
        { name: "formate pFBA", color: PAL.green, points: pf.rows.map(r => [r.o2_max, r.for]) },
        { name: "formate FBA (one solver path)", color: PAL.slate, points: fb.rows.map(r => [r.o2_max, r.for]), dash: "5 3" },
      ], ylabel: "secretion flux"
    })) +
    card("Rerun", cmd("uv run python exp7_pfba.py"));
}

async function pSubs(v) {
  const d = await api("/api/data/substrates");
  const rows = d.rows;
  const aer = rows.filter(r => r.condition === "aerobic"), ana = rows.filter(r => r.condition === "anaerobic");
  const cpct = Object.keys(rows[0]).filter(c => c.startsWith("Cpct_"));
  const nic = c => c.replace("Cpct_EX_", "").replace("_e", "").replace("co2", "CO2");
  const cats = ana.map(r => ({
    label: r.substrate,
    segments: cpct.map(c => ({ name: nic(c), value: r[c] || 0, color: PRODUCT_COLORS[nic(c)] || PAL.steel }))
  }));
  v.innerHTML = head("Substrates", "Equal carbon uptake (60 C-mmol), aerobic + anaerobic. Yield tracks redox state.") +
    `<div class="grid2">` +
    card("Yield vs degree of reduction per C", scatter({
      series: [
        { name: "aerobic", color: PAL.blue, points: aer.map(r => ({ x: r.DoR_C, y: r.Y_per_Cmol, label: r.substrate })) },
        { name: "anaerobic", color: PAL.amber, shape: "square", points: ana.map(r => ({ x: r.DoR_C, y: r.Y_per_Cmol, label: r.substrate })) },
      ], ylabel: "yield (gDW / C-mol)"
    })) +
    card("Anaerobic product spectra (% C)", stackedBars({ categories: cats, ylabel: "% of carbon taken up" })) +
    `</div>` +
    card("Table", dataTable(
      [["substrate", "Substrate"], ["condition", "Cond"], ["DoR_C", "DoR/C"], ["growth", "Growth"], ["Y_per_Cmol", "Y/C-mol"]],
      rows, { num: [0, 0, 1, 1, 1], dec: [0, 0, 2, 4, 5] })) +
    card("Reading", `<p class="muted">Glycerol (most reduced) abandons acetate entirely anaerobically and growth collapses; acetate and succinate cannot ferment (mu = 0); pyruvate needs no ethanol. DoR is computed on model species at physiological protonation.</p>`) +
    card("Rerun", cmd("uv run python exp9_substrates.py"));
}

async function pRepro(v) {
  v.innerHTML = head("Reproduce", "Every experiment reruns from a shell in the project folder.") +
    card("Commands", cmd(`cd C:\\Users\\gurur\\OneDrive\\Documents\\metabolism
uv run python exp1_aerobic_anaerobic.py  # core aer vs ana
uv run python exp2_o2_sweep.py           # O2 sweep 0-20
uv run python exp3_followups.py          # plateau + kink ID
uv run python exp4_fva_kink.py           # FVA + degeneracy probe
uv run python exp5_genome_scale.py       # iML1515 repeat
uv run python exp6_anchor.py             # literature anchor
uv run python exp7_pfba.py               # pFBA + loopless
uv run python exp8_knockouts.py          # KO screen vs DEG
uv run python exp9_substrates.py         # substrates + DoR
uv run python exp16_lactate.py           # lactate tradeoff (growth vs lac)
uv run python exp17_maintenance.py       # ATPM sweep core vs 1515
uv run python exp18_kla.py               # dFBA with O2 gas transfer
uv run python exp19_strain.py            # double-KO succinate scan + MOMA
uv run python exp20_biomass_c.py         # explicit biomass carbon
uv run python exp21_kink.py              # 14.7-kink flux vectors
uv run uvicorn server:app --port 8123    # this tool (8123; 8000 is OS-reserved)`)) +
    card("References", `<ul><li>Varma &amp; Palsson 1994, AEM 60:3724-3731 (yields, uptakes)</li><li>J. Bacteriol. 182:620-626 (2000) (anaerobic product ratios)</li><li>Baba et al. 2006 (Keio collection); DEG 15.0 (essential genes)</li><li>Monk et al. 2017 (iML1515); Lewis et al. 2010 (pFBA)</li><li>Mahadevan et al. 2002 (dFBA); Segre et al. 2002 (MOMA)</li></ul><p class="muted">Result log with bugfixes: <code class="inline">notes.md</code>. New datasets (lactate_tradeoff, maintenance_sweep, dfba_kla, strain_doubles, kink_*) are served under /api/data/*; biomass + kLa endpoints under /api/biomass_carbon and /api/dfba/kla.</p>`);
}

async function pGuide(v) {
  v.innerHTML = head("Guide: start here", "What this tool is, how to read it, and what to try first.") +
    card("What am I looking at?", `<p>This is a workbench for <b>constraint-based metabolic modeling</b> of <i>E. coli</i>. Each page is one experiment: first the result, then the data behind it, then the command that reproduces it. Nothing here is hand-drawn - every number comes from solving a model with COBRApy, either precomputed (CSV records) or live in your session.</p>`) +
    card("FBA in 60 seconds", `<p><b>Flux Balance Analysis</b> treats metabolism as a flow network. Reactions carry flows (fluxes, in mmol/gDW/h). At steady state every internal metabolite is produced as fast as it is consumed. We then ask a solver: <i>given limits on food and oxygen, what flow pattern maximizes growth?</i> That is a linear program, solved in milliseconds.</p><p>Two models are used: <b>core</b> (72 metabolites, fast, good for learning) and <b>iML1515</b> (genome scale, 2712 reactions, realistic yields). Growth rate (mu, 1/h) is the objective: grams of new cells per gram of cells per hour.</p>`) +
    card("How to read the numbers", dataTable(
      [["s", "Symbol"], ["m", "Meaning"]],
      [
        { s: "flux -10", m: "uptake of 10 units (negative = into the cell)" },
        { s: "flux +8.5", m: "secretion of 8.5 units (positive = out of the cell)" },
        { s: "mu 0.87/h", m: "growth rate; cells double roughly every 48 minutes" },
        { s: "EX_glc__D_e", m: "exchange reaction: glucose crossing the cell boundary" },
        { s: "PFL / PDH", m: "two enzymes competing for pyruvate (fermentation vs respiration)" },
      ])) +
    card("Suggested path", `<ul><li><b>Aerobic vs anaerobic</b> - the founding comparison. Read the redox box.</li><li><b>O2 sweep lab</b> - drag the slider from 0 to 25 and watch fermentation die in stages.</li><li><b>Batch culture</b> - the same biology playing out over time: overflow, then cleanup.</li><li><b>Knockouts</b> - search hemN, then break tpiA two different ways (FBA vs MOMA).</li><li><b>Literature anchor</b> - where predictions meet measured cells, misses included.</li></ul>`) +
    card("Vocabulary", dataTable(
      [["t", "Term"], ["m", "Meaning"]],
      [
        { t: "LP", m: "linear program; the math FBA solves" },
        { t: "pFBA", m: "among optimal states, pick the one with least total flow" },
        { t: "FVA", m: "min/max each flux can take while staying optimal" },
        { t: "Sampling", m: "draw many feasible states to see distributions, not points" },
        { t: "dFBA", m: "FBA stepped through time as food runs out" },
        { t: "MOMA", m: "knockout prediction that stays near the wild-type state" },
        { t: "GPR", m: "gene-protein-reaction rule: which genes back each reaction" },
        { t: "Essential", m: "knockout growth below 1% of wild type" },
      ]));
}

async function pSampling(v) {
  const [s0, s14] = await Promise.all([api("/api/data/sampling_o2_0"), api("/api/data/sampling_o2_14")]);
  const col = (rows, c) => rows.map(r => r[c]).filter(x => typeof x === "number");
  const stats = a => {
    const m = a.reduce((x, y) => x + y, 0) / a.length;
    const sd = Math.sqrt(a.reduce((x, y) => x + (y - m) * (y - m), 0) / a.length);
    return [m, sd, Math.min(...a), Math.max(...a)];
  };
  const bio0 = s0.rows[0] ? Object.keys(s0.rows[0]).find(k => k.toLowerCase().includes("biomass")) : null;
  v.innerHTML = head("Sampling", "1000 near-optimal states per condition (core, >=95% optimal growth). Points become distributions.") +
    `<div class="grid2">` +
    card("PFL flux, anaerobic (tight)", histogram({ values: col(s0.rows, "PFL"), color: PAL.blue, title: "one way to ferment: PFL around 17.2" })) +
    card("PFL flux, O2 = 14 (spread)", histogram({ values: col(s14.rows, "PFL"), color: PAL.green, title: "split is flexible: 0 to 3.4 across optima" })) +
    `</div><div class="grid2">` +
    card("PDH flux, O2 = 14", histogram({ values: col(s14.rows, "PDH"), color: PAL.blue, title: "respiratory arm takes up the slack, 7.5 to 13.1" })) +
    card("Formate secretion, O2 = 14", histogram({ values: col(s14.rows, "EX_for_e"), color: PAL.teal, title: "mirrors PFL one-to-one" })) +
    `</div>` +
    card("Summary statistics", dataTable(
      [["c", "Condition"], ["r", "Reaction"], ["m", "Mean"], ["s", "Std"], ["n", "Min"], ["x", "Max"]],
      [["anaerobic", "PFL", ...stats(col(s0.rows, "PFL"))],
       ["anaerobic", "PDH", ...stats(col(s0.rows, "PDH"))],
       ["O2=14", "PFL", ...stats(col(s14.rows, "PFL"))],
       ["O2=14", "PDH", ...stats(col(s14.rows, "PDH"))],
       ["O2=14", "formate out", ...stats(col(s14.rows, "EX_for_e"))],
       ["O2=14", "acetate out", ...stats(col(s14.rows, "EX_ac_e"))]].map(r => ({ c: r[0], r: r[1], m: r[2], s: r[3], n: r[4], x: r[5] })),
      { num: [0, 0, 1, 1, 1, 1], dec: [0, 0, 3, 3, 3, 3] })) +
    card("Reading", `<p class="muted">Anaerobically the optimum is essentially a point (PFL 17.2 +/- 0.3). At O2 = 14 the PFL/PDH split roams freely at identical growth - this is why single-solver paths disagreed about when formate runs out, and why the growth curve kinks while flux paths smear.</p>`) +
    card("Rerun", cmd("uv run python exp10_sampling.py"));
}

async function pDfba(v) {
  const [aer, ana] = await Promise.all([api("/api/data/dfba_aerobic"), api("/api/data/dfba_anaerobic")]);
  const mets = rows => {
    const out = [
      { name: "glucose (mM)", color: PAL.blue, points: rows.map(r => [r.t, r.glc]) },
      { name: "acetate (mM)", color: PAL.amber, points: rows.map(r => [r.t, r.ac]) },
    ];
    if (Math.max(...rows.map(r => r.for)) > 0.01)
      out.push({ name: "formate (mM)", color: PAL.green, points: rows.map(r => [r.t, r.for]) });
    if (Math.max(...rows.map(r => r.etoh)) > 0.01)
      out.push({ name: "ethanol (mM)", color: PAL.red, points: rows.map(r => [r.t, r.etoh]) });
    return out;
  };
  const bio = rows => [{ name: "biomass (g/L)", color: PAL.ink, points: rows.map(r => [r.t, r.X]) }];
  v.innerHTML = head("Batch culture", "Dynamic FBA: FBA stepped through time as glucose runs out. Aerobic default caps O2 at 15 (measured max).") +
    card("Record: aerobic batch (glc 10 mM, O2 cap 15)", lineChart({ series: mets(aer.rows), ylabel: "mM" }) + lineChart({ series: bio(aer.rows), ylabel: "g/L" })) +
    card("Record: anaerobic batch", lineChart({ series: mets(ana.rows), ylabel: "mM" }) + lineChart({ series: bio(ana.rows), ylabel: "g/L" })) +
    card("Run your own batch", `
      <div class="grid2"><div>
      <label class="field">O2 cap (aerobic only)</label><input type="text" id="dO2" value="15">
      <label class="field">Initial glucose (mM)</label><input type="text" id="dGlc" value="10">
      </div><div>
      <label class="field">Horizon (h, max 30)</label><input type="text" id="dT" value="14">
      <label class="field">Condition</label><select id="dAna"><option value="false">aerobic</option><option value="true">anaerobic</option></select>
      </div></div>
      <button class="btn primary" id="dRun">Run batch (~10-20 s)</button>
      <div id="dOut" style="margin-top:12px"></div>
      <p class="muted">Euler integration, Monod uptake bounds. O2 is a flux cap, not a gas balance - see exp11 header for limits.</p>`) +
    card("Reading", `<p class="muted">Aerobically: glucose depletes, acetate humps to ~7 mM then gets re-eaten (overflow plus diauxie, as Varma &amp; Palsson observed). Anaerobically: glucose becomes the trio and growth stalls near 0.3 g/L. Try O2 cap 5 vs 25 and watch the acetate hump shrink.</p>`) +
    card("Rerun", cmd("uv run python exp11_dfba.py"));
  longRun(document.getElementById("dRun"), document.getElementById("dOut"), async (sig) => {
    const q = `o2cap=${encodeURIComponent(document.getElementById("dO2").value)}&glc0=${encodeURIComponent(document.getElementById("dGlc").value)}&T=${encodeURIComponent(document.getElementById("dT").value)}&anaerobic=${document.getElementById("dAna").value}`;
    const rows = await api(`/api/dfba/run?${q}`, { signal: sig });
    if (sig.aborted) return;
    document.getElementById("dOut").innerHTML = lineChart({ series: mets(rows), ylabel: "mM" }) + lineChart({ series: bio(rows), ylabel: "g/L" });
  });
}

const CLASS_COLORS = { bookkeeping: "#6b7484", carrier: "#8b96ab", pathway: "#5ea0f2" };
const BIN_COLORS = { lethal: "#f06666", crippling: "#e5a63d", mild: "#5ea0f2", none: "#5b6b82" };

async function pNetwork(v) {
  const d = await api("/api/data/degrees");
  const rows = d.rows;
  const stat = a => {
    const s = [...a].sort((x, y) => x - y);
    const mid = s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2;
    return [mid, s.reduce((x, y) => x + y, 0) / s.length];
  };
  const all = rows.map(r => r.degree), pw = rows.filter(r => r.class === "pathway").map(r => r.degree);
  const [medA, meanA] = stat(all), [medP, meanP] = stat(pw);
  v.innerHTML = head("Network hubs", "Metabolites ranked by reaction count (e_coli_core, 72 nodes). Currency first, then the real hubs.") +
    `<div class="metrics" style="margin-bottom:16px">
      <div class="metric"><div class="l">Median / mean degree</div><div class="v">${medA.toFixed(0)} / ${meanA.toFixed(2)}</div><div class="d muted">with currency</div></div>
      <div class="metric"><div class="l">Median / mean, pathway only</div><div class="v">${medP.toFixed(0)} / ${meanP.toFixed(2)}</div><div class="d muted">currency excluded</div></div>
      <div class="metric"><div class="l">Top hub</div><div class="v" style="font-size:16px">h_c (35), then pyruvate (11)</div><div class="d muted">bookkeeping vs real</div></div>
    </div>
    <div class="grid2">` +
    card(`Top 15 <span class="muted" style="font-weight:400">- toggle currency</span>
      <div style="margin:6px 0 10px;font-size:13px">
      <label><input type="checkbox" id="tBook" checked> bookkeeping</label>
      <label style="margin-left:14px"><input type="checkbox" id="tCar" checked> carriers</label>
      </div><div id="top15"></div>` + legendHTML([["bookkeeping", CLASS_COLORS.bookkeeping], ["carrier", CLASS_COLORS.carrier], ["pathway hub", CLASS_COLORS.pathway]])) +
    card("Full degree distribution", histogram({ values: all, bins: 18, color: PAL.blue, title: "most metabolites touch 1-4 reactions; a few touch 10+" })) +
    `</div>` +
    card("Which metabolites count as currency, and why", `<ul><li><b>Bookkeeping (excluded first):</b> protons and water in every compartment. They balance redox and hydrolysis equations, not pathway logic.</li><li><b>Carriers (excluded second):</b> ATP/ADP/AMP, Pi/PPi, NAD(H), NADP(H), CoA. Group shuttles reused across unrelated pathways; their connectivity measures bookkeeping, not control.</li><li><b>Kept as hubs:</b> pyruvate, PEP, acetyl-CoA, TCA acids - carbon skeletons whose connections are the pathway structure itself. Judgment call on record: CO2 stays (carbon sink with pathway-specific meaning); CoA goes (pure acyl shuttle).</li></ul>`) +
    card("Reading: organization and the scale-free criticism", `<p><b>Shape:</b> a steep right skew - most nodes peripheral, a few hubs (pyruvate, PEP, acetyl-CoA) integrate traffic. That is the bow-tie/hourglass of metabolism: diverse inputs funnel through a dozen precursors, then fan out to biomass. Robust to random enzyme loss, fragile exactly at the hubs - which is why the deletion screen kills gapA/pgk/eno.</p><p class="muted"><b>Standard criticism of "scale-free":</b> 72 nodes cannot establish a power law; a straight-ish line on log-log paper is not evidence (Clauset-Shalizi-Newman); the result depends on the subjective currency decision; log-normal and truncated fits do as well; and no preferential-attachment mechanism in metabolism is established. Say "hub-dominated", not "scale-free".</p>`) +
    card("Rerun", cmd("uv run python exp13_network.py"));
  const render = () => {
    const showB = document.getElementById("tBook").checked, showC = document.getElementById("tCar").checked;
    const filt = rows.filter(r => r.class === "pathway" || (r.class === "bookkeeping" && showB) || (r.class === "carrier" && showC)).slice(0, 15);
    document.getElementById("top15").innerHTML = hbars({
      items: filt.map(r => ({ label: r.met, value: r.degree, color: CLASS_COLORS[r.class] }))
    });
  };
  document.getElementById("tBook").addEventListener("change", render);
  document.getElementById("tCar").addEventListener("change", render);
  render();
}

const WHY_LETHAL = {
  b1779: "Sole bridge from upper glycolysis, PPP and ED pathway into lower glycolysis; every downward carbon atom passes through glyceraldehyde-3-P.",
  b2926: "Next step in the same unbranched chain; also the first ATP payoff of glycolysis. No isozyme in core.",
  b2779: "Last common step to PEP and pyruvate; no isozyme in the core reconstruction.",
  b0720: "Only entry into the TCA cycle. Without citrate: no 2-oxoglutarate, no glutamate family, no TCA NADH.",
  b1136: "Only modeled route to 2-oxoglutarate; blocks AKGDH and everything downstream of it."
};

async function pDeletions(v) {
  const [ko, info] = await Promise.all([api("/api/data/core_ko"), api("/api/core_gene_info")]);
  const rows = [...ko.rows].sort((a, b) => a.frac - b.frac);
  const bins = { lethal: 0, crippling: 0, mild: 0, none: 0 };
  rows.forEach(r => bins[r.bin]++);
  const leth = rows.filter(r => r.bin === "lethal");
  v.innerHTML = head("Gene deletions (core)", "137 single knockouts on glucose minimal aerobic, as fractions of wild-type growth (0.874).") +
    card("Prediction check", `<p>Your pre-registered prediction: <b>almost none (&lt;5)</b>. Result: <b>5 lethal</b> - right on the boundary, and 101 of 137 genes (74%) with no effect at all. The redundancy instinct was essentially right.</p>`) +
    `<div class="metrics" style="margin-bottom:16px">
      <div class="metric"><div class="l">Lethal &lt;1%</div><div class="v">${bins.lethal}</div></div>
      <div class="metric"><div class="l">Crippling 1-50%</div><div class="v">${bins.crippling}</div></div>
      <div class="metric"><div class="l">Mild 50-95%</div><div class="v">${bins.mild}</div></div>
      <div class="metric"><div class="l">No effect &gt;95%</div><div class="v">${bins.none}</div></div>
    </div>` +
    card("All genes, sorted by growth fraction (hover for names)", bars({
      items: rows.map(r => ({ label: `${r.gene} (${r.name})`, value: r.frac, color: BIN_COLORS[r.bin] })),
      ylabel: "fraction of wild type", xlabel: "genes, worst knockout first",
      legend: [["lethal", BIN_COLORS.lethal], ["crippling", BIN_COLORS.crippling], ["mild", BIN_COLORS.mild], ["no effect", BIN_COLORS.none]]
    })) +
    card("The 5 lethals: what they do and why nothing bypasses them", dataTable(
      [["g", "Gene"], ["r", "Reaction"], ["w", "Why no alternative"]],
      leth.map(r => ({
        g: `${r.gene} (${r.name})`,
        r: (info[r.gene] ? info[r.gene].reactions.map(x => x.id).join(", ") : "-"),
        w: WHY_LETHAL[r.gene] || ""
      })))) +
    card("Why the other 132 survive", `<p class="muted">Isozymes where the gene-protein-reaction rule lists them (pfkA/pfkB, pta/eutD, ackA/tdcD); parallel routes (PGI bypassed via the ED pathway and PPP, hence ~99% growth); partial function (tpiA strands DHAP but GAP still flows, so crippled at 0.80, not dead). Compare the genome-scale screen (Knockouts page): 196 lethals there, mostly biosynthesis the core model doesn't represent.</p>`) +
    card("Honest caveats", `<ul><li>In-silico essential means lethal <b>in this model, medium and objective</b> - change any and calls change.</li><li>Missing isozymes in the annotation cause false lethals; phantom bypasses the cell never uses cause false viables (our genome screen missed eno/fbaA/gapA/pgk exactly this way).</li><li>Regulation is invisible: a bypass that exists but stays switched off still counts.</li><li>FBA models the <b>adapted</b> mutant; fresh knockouts follow MOMA (see Knockouts page).</li><li>Non-metabolic essentiality (replication, envelope) is out of scope by construction.</li></ul>`) +
    card("Rerun", cmd("uv run python exp14_core_ko.py"));
}

async function pCarbon(v) {
  const a = await api("/api/carbon_accounting");
  const bioPct = 100 * a.c_biomass / a.c_in;
  v.innerHTML = head("Carbon accounting", "Aerobic core, glucose -10. Do the arithmetic yourself - check each step before revealing.") +
    card("Scope", `<p><b>Model predictions under one growth condition</b> - optimal aerobic growth on glucose minimal. Not measured fluxes: real cells run regulation, kinetics and maintenance this LP doesn't see.</p>`) +
    card("Step 1 - carbon in", `<p>Glucose uptake is ${fmt(a.glc, 2)} mmol. Glucose is C6. Carbon in (C-mmol)?</p>
      <input type="text" id="c1" style="max-width:140px"> <button class="btn" id="c1b">Check</button> <span id="c1o"></span>`) +
    card("Step 2 - the G6P split", `<p>PGI flux is ${fmt(a.pgi, 2)}, G6PDH2r flux is ${fmt(a.g6pdh, 2)} (mmol). What share of glucose goes through the pentose phosphate pathway (%)?</p>
      <input type="text" id="c2" style="max-width:140px"> <button class="btn" id="c2b">Check</button> <span id="c2o"></span>`) +
    card("Step 3 - CO2 inventory", `<p>Sum the internal rows (CO2t is the export step, not production - excluded from the sum). Net CO2?</p>` +
      dataTable([["reaction", "Reaction"], ["coeff", "Coeff"], ["flux", "Flux"], ["co2", "CO2"]],
        a.co2_reactions, { num: [0, 1, 1, 1], dec: [0, 0, 2, 2] }) +
      `<p style="margin-top:8px">Net internal CO2 = <input type="text" id="c3" style="max-width:140px"> <button class="btn" id="c3b">Check</button> <span id="c3o"></span></p>`) +
    card("Step 4 - close the balance", `<p>Nothing carbonaceous is secreted except CO2 (check the Aerobic page). Biomass carbon, as % of uptake?</p>
      <input type="text" id="c4" style="max-width:140px"> <button class="btn" id="c4b">Check</button> <span id="c4o"></span>
      <div><button class="btn primary" id="cRev">Show the accounting</button></div><div id="cAr"></div>`) +
    card("Flow diagram (C-mmol/h)", sankey({
      total: a.c_in,
      source: { label: "glucose", value: a.sankey.glc_c, color: PAL.blue },
      split: [
        { label: "glycolysis (PGI)", value: a.sankey.pgi_c, color: PAL.blue },
        { label: "PPP (G6PDH2r)", value: a.sankey.ppp_c, color: PAL.teal },
        { label: "other G6P uses", value: a.sankey.other_c, color: PAL.light },
      ],
      sinks: [
        { label: "biomass", value: a.sankey.bio_c, color: PAL.green },
        { label: "CO2", value: a.sankey.co2_c, color: PAL.slate },
      ]
    }) + `<p class="muted">Simplification on record: branches reconverge at "downstream" because exact per-pathway carbon fate needs 13C tracing, not FBA. Widths are exact.</p>`) +
    card("Why is the PPP share so large?", `<p>Nearly half the glucose (${fmt(a.g6pdh_pct, 1)}%) goes through oxidative PPP. Textbook diagrams draw glycolysis as the main road because they depict the carbon backbone - but growth also needs <b>NADPH</b> for reductive biosynthesis and ribose for nucleotides, and oxPPP is the cheapest NADPH source in this model. Measured oxPPP shares are lower (~20-30%): real cells use transhydrogenase and regulation the optimum ignores. That gap is the model-vs-measurement flag above, made concrete.</p>`) +
    card("Rerun", cmd("uv run python exp15_carbon_accounting.py"));
  const chk = (inp, btn, out, expected, tol, ok) => {
    document.getElementById(btn).addEventListener("click", () => {
      const v = parseFloat(document.getElementById(inp).value);
      const el = document.getElementById(out);
      if (isFinite(v) && Math.abs(v - expected) <= tol) { el.innerHTML = `<span class="pill ok">correct</span> ${ok}`; }
      else { el.innerHTML = `<span class="pill bad">not quite</span> <span class="muted">expected ${expected}</span>`; }
    });
  };
  chk("c1", "c1b", "c1o", a.c_in, 0.5, "C-mmol in.");
  chk("c2", "c2b", "c2o", a.g6pdh_pct, 1.0, "% through oxPPP.");
  chk("c3", "c3b", "c3o", a.co2_net, 0.05, `= EX_co2_e (${fmt(a.ex_co2, 2)}). Inventory closes.`);
  chk("c4", "c4b", "c4o", bioPct, 1.0, "% of carbon becomes cells.");
  document.getElementById("cRev").addEventListener("click", () => {
    document.getElementById("cAr").innerHTML = `<pre class="cmd">in:      ${fmt(a.c_in, 2)} C-mmol (glucose ${fmt(a.glc, 2)} x 6)
CO2:     ${fmt(a.c_co2, 2)} C-mmol (${fmt(100 * a.c_co2 / a.c_in, 1)}%)
biomass: ${fmt(a.c_biomass, 2)} C-mmol (${fmt(bioPct, 1)}%, remainder)
check:   gross CO2 ${fmt(a.co2_reactions.filter(x => x.co2 > 0 && x.reaction !== "CO2t").reduce((s, x) => s + x.co2, 0), 2)} - PPC refix ${fmt(-a.co2_reactions.find(x => x.reaction === "PPC").co2, 2)} = net ${fmt(a.co2_net, 2)} = EX_co2_e</pre>`;
  });
}

let _escherLib = null, _escherMap = null, _escherBuilder = null;
function loadScript(src) {
  return new Promise((res, rej) => {
    if (document.querySelector(`script[data-vendor="${src}"]`)) return res();
    const s = document.createElement("script");
    s.src = src; s.dataset.vendor = src;
    s.onload = res; s.onerror = () => rej(new Error(`failed to load ${src}`));
    document.head.appendChild(s);
  });
}
// API-first: Escher library + map stream from CDN on first use, nothing
// vendored (keeps the repo light).
const ESCHER_CDN = "https://cdn.jsdelivr.net/npm/escher@1.8.2/dist/escher.min.js";
const ESCHER_MAP = "https://escher.github.io/1-0-0/2/maps/Escherichia%20coli/e_coli_core.Core%20metabolism.json";
async function escherReady() {
  if (!_escherLib) {
    await loadScript(ESCHER_CDN);
    _escherLib = window.escher;
    if (!_escherLib || !_escherLib.Builder) throw new Error("Escher library failed to initialise");
  }
  if (!_escherMap) {
    const r = await fetch(ESCHER_MAP);
    if (!r.ok) throw new Error("map download failed");
    _escherMap = await r.json();
  }
  return _escherLib;
}
const FM_PRESETS = [
  ["Aerobic (glc 10, O2 25)", "core", 25, 10],
  ["Anaerobic (glc 10)", "core", 0, 10],
  ["V&P aerobic (glc 10.5, O2 15)", "core", 15, 10.5],
  ["V&P anaerobic (glc 18.5)", "core", 0, 18.5],
];
async function pFluxmap(v) {
  const genes = await api("/api/core_genes");
  v.innerHTML = head("Flux map", "Live FBA fluxes drawn on the E. coli core pathway map (Escher, BiGG layout). Arrow width and color follow flux magnitude and direction; switch presets or knock out a gene to watch overflow and fermentation reroute.") +
    card("Condition", `
      <div class="grid2">
      <div><label class="field">Preset</label>
      <select id="fmpreset">${FM_PRESETS.map((p, i) => `<option value="${i}">${p[0]}</option>`).join("")}</select></div>
      <div><label class="field">Knock out (optional)</label>
      <select id="fmgene"><option value="">none</option>${genes.map(g => `<option>${g}</option>`).join("")}</select></div>
      </div>
      <div style="margin-top:10px"><button class="btn primary" id="fmdraw">Draw map</button></div>
      <div class="metrics" style="margin-top:12px">
        <div class="metric"><div class="l">Growth</div><div class="v" id="fmGrowth">-</div></div>
        <div class="metric"><div class="l">Solve</div><div class="v" id="fmStatus">-</div></div>
        <div class="metric"><div class="l">On map</div><div class="v" id="fmCount">-</div></div>
      </div>`) +
    card("Map", `<div id="escher-box"><div id="escher-map"></div></div><p class="muted" id="fmnote">Press Draw map.</p>`) +
    card("Rerun", cmd("uv run uvicorn server:app --port 8123  # then open the Flux map page"));
  document.getElementById("fmdraw").addEventListener("click", async () => {
    const note = document.getElementById("fmnote");
    note.textContent = "Solving and drawing…";
    try {
      const E = await escherReady();
      const [, model, o2max, glc] = FM_PRESETS[+document.getElementById("fmpreset").value];
      const gene = document.getElementById("fmgene").value;
      const sol = await api(`/api/solve/fluxes?model=${model}&o2max=${o2max}&glc=${glc}&gene=${encodeURIComponent(gene)}`);
      document.getElementById("fmGrowth").textContent = fmt(sol.growth, 4);
      document.getElementById("fmStatus").textContent = sol.status;
      if (!_escherBuilder) {
        _escherBuilder = new E.Builder(_escherMap, null, null,
          document.getElementById("escher-map"),
          { menu: "zoom", enable_editing: false, fill_screen: false, scroll_behavior: "zoom" });
      }
      _escherBuilder.set_reaction_data(sol.fluxes);
      const ids = new Set(Object.values(_escherMap[1].reactions).map(r => r.bigg_id));
      const n = Object.keys(sol.fluxes).filter(k => ids.has(k)).length;
      document.getElementById("fmCount").textContent = `${n} reactions`;
      note.textContent = gene ? `Δ${gene}: compare against the no-KO preset to see rerouting.`
        : "Negative fluxes run against the drawn arrow direction.";
    } catch (e) { note.textContent = `Could not draw: ${e.message}`; }
  });
}

const PAGES = { guide: pGuide, overview: pOverview, aerana: pAerana, carbon: pCarbon, o2lab: pO2lab, sampling: pSampling, dfba: pDfba, fluxmap: pFluxmap, genome: pGenome, network: pNetwork, anchor: pAnchor, ko: pKO, deletions: pDeletions, pfba: pPfba, subs: pSubs, repro: pRepro };

function toast(msg, bad) {
  const t = document.createElement("div");
  t.className = "toast" + (bad ? " bad" : "");
  t.textContent = msg;
  document.getElementById("toasts").appendChild(t);
  setTimeout(() => t.remove(), 4200);
}

const SKEL = `<div class="pagehead"><h1>&nbsp;</h1><p><span class="skel" style="display:block;width:min(46ch,90%)"></span></p></div>
  <div class="card"><div class="skel" style="height:20px;width:36%"></div><div class="skel"></div><div class="skel" style="width:82%"></div></div>
  <div class="card"><div class="skel" style="height:120px"></div></div>`;

(function init() {
  const nav = document.getElementById("nav"), view = document.getElementById("view");
  const labels = {};
  NAV.forEach(([id, label]) => {
    if (id === "sec") { nav.insertAdjacentHTML("beforeend", `<div class="navsec">${label}</div>`); return; }
    labels[id] = label;
    const b = document.createElement("button");
    b.textContent = label; b.dataset.page = id;
    b.addEventListener("click", () => go(id));
    nav.appendChild(b);
  });
  let navSeq = 0;
  async function go(id) {
    if (!PAGES[id]) return;
    const my = ++navSeq;
    nav.querySelectorAll("button").forEach(x => x.classList.toggle("active", x.dataset.page === id));
    view.classList.remove("enter");
    view.innerHTML = SKEL;
    document.title = `${labels[id] || id} — Oxalis`;
    let failed = null;
    try { await PAGES[id](view); } catch (e) { failed = e; }
    if (my !== navSeq) return;
    if (failed) {
      view.innerHTML = head("Error", "") + `<p class="err">${esc(failed.message)}</p>`;
      toast(`Failed to load ${labels[id] || id}: ${failed.message}`, true);
    }
    view.classList.add("enter");
    document.getElementById("main").scrollTop = 0;
    window.scrollTo(0, 0);
  }
  // command palette: jump to any page
  const pal = document.getElementById("pal"), palin = document.getElementById("palin"),
    palitems = document.getElementById("palitems");
  const entries = NAV.filter(([id]) => id !== "sec");
  let sel = 0, shown = entries;
  function draw() {
    palitems.innerHTML = "";
    shown.forEach(([id, label], i) => {
      const b = document.createElement("button");
      b.innerHTML = `<small>${id}</small>${esc(label)}`;
      if (i === sel) b.classList.add("sel");
      b.addEventListener("click", () => { closePal(); go(id); });
      palitems.appendChild(b);
    });
  }
  function openPal() {
    pal.classList.add("open"); palin.value = "";
    shown = entries; sel = 0; draw();
    setTimeout(() => palin.focus(), 0);
  }
  function closePal() { pal.classList.remove("open"); }
  palin.addEventListener("input", () => {
    const q = palin.value.trim().toLowerCase();
    shown = entries.filter(([id, label]) => label.toLowerCase().includes(q) || id.includes(q));
    sel = 0; draw();
  });
  palin.addEventListener("keydown", e => {
    if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(sel + 1, shown.length - 1); draw(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(sel - 1, 0); draw(); }
    else if (e.key === "Enter" && shown[sel]) { closePal(); go(shown[sel][0]); }
  });
  pal.addEventListener("click", e => { if (e.target === pal) closePal(); });
  document.getElementById("palbtn").addEventListener("click", openPal);
  document.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); pal.classList.contains("open") ? closePal() : openPal(); }
    else if (e.key === "Escape") closePal();
  });
  // backend liveness dot
  api("/api/growth_comparison").catch(() => document.getElementById("livedot").classList.add("dead"));
  go("overview");
})();
