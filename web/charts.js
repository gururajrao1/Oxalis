/* Minimal SVG chart helpers. No dependencies. */
const PAL = {
  ink: "#e9edf4", muted: "#99a2b4", grid: "#1a2230", line: "#2a3448",
  blue: "#5ea0f2", teal: "#2dd4bf", amber: "#e5a63d", green: "#4ade80",
  red: "#f06666", brown: "#c09a5e", slate: "#8b96ab", light: "#7c879c",
  steel: "#7d8aa0"
};
const PRODUCT_COLORS = {
  acetate: PAL.blue, ethanol: PAL.amber, formate: PAL.green,
  lactate: PAL.red, succinate: PAL.brown, CO2: PAL.slate,
  co2: PAL.slate, biomass: PAL.light, other: "#aab4c4", pyruvate: PAL.steel,
  methanol: PAL.teal, for: PAL.green, ac: PAL.blue, succ: PAL.brown
};

function fmt(n, d = 2) {
  if (n === null || n === undefined || isNaN(n)) return "-";
  return Number(n).toFixed(d);
}
function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;"); }

function ticks(min, max, n) {
  if (min === max) { min -= 1; max += 1; }
  const out = [];
  for (let i = 0; i <= n; i++) out.push(min + (max - min) * i / n);
  return out;
}
function legendHTML(items) {
  return `<div class="legend">` + items.map(([n, c]) =>
    `<span><i style="background:${c}"></i>${esc(n)}</span>`).join("") + `</div>`;
}

function lineChart(o) {
  const W = o.w || 640, H = o.h || 300, M = { l: 48, r: 14, t: 12, b: 34 };
  const iw = W - M.l - M.r, ih = H - M.t - M.b;
  let xs = [], ys = [];
  o.series.forEach(s => s.points.forEach(p => { xs.push(p[0]); ys.push(p[1]); }));
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  let y0 = Math.min(0, ...ys), y1 = Math.max(...ys);
  if (y1 === y0) y1 = y0 + 1;
  y1 += (y1 - y0) * 0.06;
  const X = x => M.l + (x - x0) / (x1 - x0 || 1) * iw;
  const Y = y => M.t + ih - (y - y0) / (y1 - y0) * ih;
  let g = "";
  ticks(y0, y1, 5).forEach(t => {
    g += `<line x1="${M.l}" y1="${Y(t)}" x2="${W - M.r}" y2="${Y(t)}" stroke="${PAL.grid}"/>`;
    g += `<text x="${M.l - 7}" y="${Y(t) + 4}" text-anchor="end" font-size="11" fill="${PAL.muted}">${fmt(t, t < 10 && t % 1 ? 2 : 1)}</text>`;
  });
  ticks(x0, x1, 6).forEach(t => {
    g += `<text x="${X(t)}" y="${H - 10}" text-anchor="middle" font-size="11" fill="${PAL.muted}">${fmt(t, 0)}</text>`;
  });
  o.series.forEach(s => {
    const pts = s.points.map(p => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(" ");
    g += `<polyline points="${pts}" fill="none" stroke="${s.color}" stroke-width="2"${s.dash ? ` stroke-dasharray="${s.dash}"` : ""}/>`;
    if (s.points.length <= 60)
      s.points.forEach(p => { g += `<circle cx="${X(p[0])}" cy="${Y(p[1])}" r="2.4" fill="${s.color}"/>`; });
  });
  const svg = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block">` +
    (o.ylabel ? `<text x="12" y="${M.t + ih / 2}" text-anchor="middle" font-size="12" fill="${PAL.muted}" transform="rotate(-90 12 ${M.t + ih / 2})">${esc(o.ylabel)}</text>` : "") +
    g + `</svg>`;
  return svg + legendHTML(o.series.map(s => [s.name, s.color]));
}

function groupedBars(o) {
  const W = o.w || 640, H = o.h || 300, M = { l: 48, r: 14, t: 12, b: 60 };
  const iw = W - M.l - M.r, ih = H - M.t - M.b;
  const max = Math.max(...o.series.flatMap(s => s.values)) * 1.12 || 1;
  const Y = v => M.t + ih - v / max * ih;
  const gw = iw / o.labels.length, bw = Math.min(34, gw / (o.series.length + 1));
  let g = "";
  ticks(0, max, 5).forEach(t => {
    g += `<line x1="${M.l}" y1="${Y(t)}" x2="${W - M.r}" y2="${Y(t)}" stroke="${PAL.grid}"/>`;
    g += `<text x="${M.l - 7}" y="${Y(t) + 4}" text-anchor="end" font-size="11" fill="${PAL.muted}">${fmt(t, 1)}</text>`;
  });
  o.labels.forEach((lb, i) => {
    o.series.forEach((s, j) => {
      const x = M.l + gw * i + gw / 2 + (j - (o.series.length - 1) / 2) * bw;
      g += `<rect x="${(x - bw / 2 + 1).toFixed(1)}" y="${Y(s.values[i]).toFixed(1)}" width="${(bw - 2).toFixed(1)}" height="${(M.t + ih - Y(s.values[i])).toFixed(1)}" fill="${s.color}"/>`;
    });
    g += `<text x="${M.l + gw * i + gw / 2}" y="${H - 34}" text-anchor="middle" font-size="11.5" fill="${PAL.muted}">${esc(lb)}</text>`;
  });
  const svg = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block">` +
    (o.ylabel ? `<text x="12" y="${M.t + ih / 2}" text-anchor="middle" font-size="12" fill="${PAL.muted}" transform="rotate(-90 12 ${M.t + ih / 2})">${esc(o.ylabel)}</text>` : "") +
    g + `</svg>`;
  return svg + legendHTML(o.series.map(s => [s.name, s.color]));
}

function stackedBars(o) {
  const W = o.w || 560, H = o.h || 320, M = { l: 48, r: 14, t: 12, b: 40 };
  const iw = W - M.l - M.r, ih = H - M.t - M.b;
  const Y = v => M.t + ih - v / 100 * ih;
  const bw = Math.min(120, iw / o.categories.length / 2.2);
  let g = "";
  ticks(0, 100, 5).forEach(t => {
    g += `<line x1="${M.l}" y1="${Y(t)}" x2="${W - M.r}" y2="${Y(t)}" stroke="${PAL.grid}"/>`;
    g += `<text x="${M.l - 7}" y="${Y(t) + 4}" text-anchor="end" font-size="11" fill="${PAL.muted}">${t}%</text>`;
  });
  o.categories.forEach((c, i) => {
    const cx = M.l + iw * (i + 0.5) / o.categories.length;
    let acc = 0;
    c.segments.forEach(s => {
      if (s.value <= 0) return;
      const y2 = Y(acc), y1 = Y(acc + s.value);
      g += `<rect x="${(cx - bw / 2).toFixed(1)}" y="${y1.toFixed(1)}" width="${bw.toFixed(1)}" height="${(y2 - y1).toFixed(1)}" fill="${s.color}"/>`;
      if (s.value >= 9)
        g += `<text x="${cx}" y="${(y1 + y2) / 2 + 4}" text-anchor="middle" font-size="11.5" fill="#fff">${s.value.toFixed(0)}%</text>`;
      acc += s.value;
    });
    g += `<text x="${cx}" y="${H - 14}" text-anchor="middle" font-size="12.5" fill="${PAL.ink}">${esc(c.label)}</text>`;
  });
  const seen = [];
  o.categories.forEach(c => c.segments.forEach(s => {
    if (s.value > 0 && !seen.find(x => x[0] === s.name)) seen.push([s.name, s.color]);
  }));
  const svg = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block">` +
    (o.ylabel ? `<text x="12" y="${M.t + ih / 2}" text-anchor="middle" font-size="12" fill="${PAL.muted}" transform="rotate(-90 12 ${M.t + ih / 2})">${esc(o.ylabel)}</text>` : "") +
    g + `</svg>`;
  return svg + legendHTML(seen);
}

function scatter(o) {
  const W = o.w || 560, H = o.h || 320, M = { l: 52, r: 60, t: 12, b: 40 };
  const iw = W - M.l - M.r, ih = H - M.t - M.b;
  const xs = o.series.flatMap(s => s.points.map(p => p.x));
  const ys = o.series.flatMap(s => s.points.map(p => p.y));
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y1 = Math.max(...ys) * 1.12 || 1;
  const X = x => M.l + (x - x0) / (x1 - x0 || 1) * iw;
  const Y = y => M.t + ih - y / y1 * ih;
  let g = "";
  ticks(0, y1, 5).forEach(t => {
    g += `<line x1="${M.l}" y1="${Y(t)}" x2="${W - M.r}" y2="${Y(t)}" stroke="${PAL.grid}"/>`;
    g += `<text x="${M.l - 7}" y="${Y(t) + 4}" text-anchor="end" font-size="11" fill="${PAL.muted}">${t.toFixed(4)}</text>`;
  });
  ticks(x0, x1, 5).forEach(t => {
    g += `<text x="${X(t)}" y="${H - 14}" text-anchor="middle" font-size="11" fill="${PAL.muted}">${t.toFixed(2)}</text>`;
  });
  o.series.forEach(s => s.points.forEach(p => {
    if (s.shape === "square")
      g += `<rect x="${X(p.x) - 4}" y="${Y(p.y) - 4}" width="8" height="8" fill="${s.color}"/>`;
    else g += `<circle cx="${X(p.x)}" cy="${Y(p.y)}" r="5" fill="${s.color}"/>`;
    g += `<text x="${X(p.x) + 8}" y="${Y(p.y) + 4}" font-size="11.5" fill="${PAL.ink}">${esc(p.label)}</text>`;
  }));
  const svg = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block">` +
    (o.ylabel ? `<text x="12" y="${M.t + ih / 2}" text-anchor="middle" font-size="12" fill="${PAL.muted}" transform="rotate(-90 12 ${M.t + ih / 2})">${esc(o.ylabel)}</text>` : "") +
    g + `</svg>`;
  return svg + legendHTML(o.series.map(s => [s.name, s.color]));
}

function confusion(o) {
  const W = 300, H = 300, M = { l: 96, r: 10, t: 30, b: 10 };
  const cw = (W - M.l - M.r) / 2, ch = (H - M.t - M.b) / 2;
  const max = Math.max(...o.matrix.flat());
  let g = "";
  const shade = v => `rgba(205,243,74,${(0.06 + 0.85 * v / max).toFixed(2)})`;
  o.matrix.forEach((row, i) => row.forEach((v, j) => {
    const x = M.l + j * cw, y = M.t + i * ch;
    g += `<rect x="${x + 2}" y="${y + 2}" width="${cw - 4}" height="${ch - 4}" fill="${shade(v)}"/>`;
    g += `<text x="${x + cw / 2}" y="${y + ch / 2 + 7}" text-anchor="middle" font-size="20" font-weight="600" fill="${v / max > 0.5 ? "#131804" : PAL.ink}">${v}</text>`;
  }));
  o.cols.forEach((c, j) => { g += `<text x="${M.l + j * cw + cw / 2}" y="16" text-anchor="middle" font-size="12" fill="${PAL.muted}">${esc(c)}</text>`; });
  o.rows.forEach((r, i) => { g += `<text x="${M.l - 8}" y="${M.t + i * ch + ch / 2 + 4}" text-anchor="end" font-size="12" fill="${PAL.muted}">${esc(r)}</text>`; });
  return `<svg viewBox="0 0 ${W} ${H}" style="width:300px;max-width:100%;height:auto;display:block">${g}</svg>`;
}

function dataTable(cols, rows, opts = {}) {
  const num = opts.num || cols.map(() => false);
  const dec = opts.dec || cols.map(() => 2);
  const maxh = opts.scroll ? ` style="max-height:${opts.scroll}px"` : "";
  let h = `<div class="scrollbox"${maxh}><table class="data"><thead><tr>`;
  cols.forEach((c, i) => { h += `<th class="${num[i] ? "num" : ""}">${esc(c[1] || c[0])}</th>`; });
  h += `</tr></thead><tbody>`;
  rows.forEach(r => {
    h += `<tr>`;
    cols.forEach((c, i) => {
      let v = r[c[0]];
      if (num[i] && typeof v === "number") v = fmt(v, dec[i]);
      if (v === null || v === undefined) v = "-";
      h += `<td class="${num[i] ? "num" : ""}">${esc(v)}</td>`;
    });
    h += `</tr>`;
  });
  return h + `</tbody></table></div>`;
}

function histogram(o) {
  const W = o.w || 300, H = o.h || 190, M = { l: 40, r: 10, t: 10, b: 32 };
  const iw = W - M.l - M.r, ih = H - M.t - M.b;
  const vals = o.values.filter(v => typeof v === "number" && isFinite(v));
  const nb = o.bins || 24;
  let mn = Math.min(...vals), mx = Math.max(...vals);
  if (mn === mx) { mn -= 0.5; mx += 0.5; }
  const counts = new Array(nb).fill(0);
  vals.forEach(v => {
    let i = Math.floor((v - mn) / (mx - mn) * nb);
    if (i >= nb) i = nb - 1;
    if (i < 0) i = 0;
    counts[i]++;
  });
  const cmax = Math.max(...counts);
  let g = "";
  const bw = iw / nb;
  counts.forEach((c, i) => {
    const h = c / cmax * ih;
    g += `<rect x="${(M.l + i * bw + 0.5).toFixed(1)}" y="${(M.t + ih - h).toFixed(1)}" width="${(bw - 1).toFixed(1)}" height="${h.toFixed(1)}" fill="${o.color || PAL.blue}"/>`;
  });
  [mn, (mn + mx) / 2, mx].forEach((t, i) => {
    g += `<text x="${M.l + iw * i / 2}" y="${H - 8}" text-anchor="middle" font-size="10.5" fill="${PAL.muted}">${fmt(t, 2)}</text>`;
  });
  g += `<text x="${M.l + iw - 2}" y="${M.t + 10}" text-anchor="end" font-size="10.5" fill="${PAL.muted}">n=${vals.length}</text>`;
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block">${g}</svg>` +
    (o.title ? `<div class="muted" style="font-size:12.5px">${esc(o.title)}</div>` : "");
}

function hbars(o) {
  const W = o.w || 560, lh = 23, M = { l: 118, r: 52, t: 8, b: 8 };
  const H = M.t + M.b + lh * o.items.length;
  const max = Math.max(...o.items.map(i => i.value));
  let g = "";
  o.items.forEach((it, i) => {
    const y = M.t + i * lh, w = Math.max(1, it.value / max * (W - M.l - M.r));
    g += `<text x="${M.l - 8}" y="${y + 16}" text-anchor="end" font-size="12" fill="${PAL.ink}">${esc(it.label)}</text>`;
    g += `<rect x="${M.l}" y="${y + 4}" width="${w.toFixed(1)}" height="13" fill="${it.color}"><title>${esc(it.label)}: ${it.value}</title></rect>`;
    g += `<text x="${M.l + w + 6}" y="${y + 16}" font-size="11.5" fill="${PAL.muted}">${it.value}</text>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block">${g}</svg>`;
}

function bars(o) {
  const W = o.w || 680, H = o.h || 250, M = { l: 44, r: 10, t: 10, b: 28 };
  const iw = W - M.l - M.r, ih = H - M.t - M.b;
  const max = Math.max(...o.items.map(i => i.value), 1);
  const bw = iw / o.items.length;
  let g = "";
  [0, 0.5, 1].forEach(t => {
    const y = M.t + ih - t / max * ih;
    g += `<line x1="${M.l}" y1="${y}" x2="${W - M.r}" y2="${y}" stroke="${PAL.grid}"/>`;
    g += `<text x="${M.l - 7}" y="${y + 4}" text-anchor="end" font-size="11" fill="${PAL.muted}">${t}</text>`;
  });
  o.items.forEach((it, i) => {
    const h = Math.max(0.5, it.value / max * ih);
    g += `<rect x="${(M.l + i * bw + 0.3).toFixed(1)}" y="${(M.t + ih - h).toFixed(1)}" width="${Math.max(0.6, bw - 0.6).toFixed(1)}" height="${h.toFixed(1)}" fill="${it.color}"><title>${esc(it.label)}: ${it.value.toFixed(3)}</title></rect>`;
  });
  g += `<text x="${M.l + iw / 2}" y="${H - 6}" text-anchor="middle" font-size="11.5" fill="${PAL.muted}">${esc(o.xlabel || "")}</text>`;
  const svg = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block">` +
    (o.ylabel ? `<text x="12" y="${M.t + ih / 2}" text-anchor="middle" font-size="12" fill="${PAL.muted}" transform="rotate(-90 12 ${M.t + ih / 2})">${esc(o.ylabel)}</text>` : "") +
    g + `</svg>`;
  return svg + (o.legend ? legendHTML(o.legend) : "");
}

function sankey(o) {
  const W = o.w || 680, H = o.h || 340, M = { l: 130, r: 130, t: 24, b: 24 };
  const iw = W - M.l - M.r;
  const cols = [M.l, M.l + iw / 3, M.l + 2 * iw / 3, W - M.r];
  const scale = (H - M.t - M.b) / o.total, cy = H / 2, NW = 16;
  const stack = items => {
    const tot = items.reduce((a, s) => a + s.value, 0);
    let y = cy - tot * scale / 2;
    return items.map(s => { const r = { ...s, y0: y, y1: y + s.value * scale }; y = r.y1; return r; });
  };
  const band = (x1, a0, a1, x2, b0, b1, color) => {
    const mx = (x1 + x2) / 2;
    return `<path d="M${x1},${a0.toFixed(1)} C${mx},${a0.toFixed(1)} ${mx},${b0.toFixed(1)} ${x2},${b0.toFixed(1)} L${x2},${b1.toFixed(1)} C${mx},${b1.toFixed(1)} ${mx},${a1.toFixed(1)} ${x1},${a1.toFixed(1)} Z" fill="${color}" opacity="0.5"></path>`;
  };
  const node = (x, s) => `<rect x="${(x - NW / 2).toFixed(1)}" y="${s.y0.toFixed(1)}" width="${NW}" height="${Math.max(1, s.y1 - s.y0).toFixed(1)}" fill="${s.color}"/>` +
    `<text x="${(x - NW / 2 - 7).toFixed(1)}" y="${((s.y0 + s.y1) / 2 + 4).toFixed(1)}" text-anchor="end" font-size="11.5" fill="${PAL.ink}">${esc(s.label)} ${s.value.toFixed(1)}</text>`;
  const nodeR = (x, s) => `<rect x="${(x - NW / 2).toFixed(1)}" y="${s.y0.toFixed(1)}" width="${NW}" height="${Math.max(1, s.y1 - s.y0).toFixed(1)}" fill="${s.color}"/>` +
    `<text x="${(x + NW / 2 + 7).toFixed(1)}" y="${((s.y0 + s.y1) / 2 + 4).toFixed(1)}" font-size="11.5" fill="${PAL.ink}">${esc(s.label)} ${s.value.toFixed(1)}</text>`;
  const src = stack([{ ...o.source }]);
  const mid = stack(o.split);
  const dst = stack([{ label: "downstream", value: o.total, color: PAL.slate }]);
  const snk = stack(o.sinks);
  let g = "";
  let sy = src[0].y0;
  mid.forEach(s => {
    const h = s.value * scale;
    g += band(cols[0] + NW / 2, sy, sy + h, cols[1] - NW / 2, s.y0, s.y1, s.color);
    sy += h;
  });
  let dy = dst[0].y0;
  mid.forEach(s => {
    const h = s.value * scale;
    g += band(cols[1] + NW / 2, s.y0, s.y1, cols[2] - NW / 2, dy, dy + h, s.color);
    dy += h;
  });
  dy = dst[0].y0;
  snk.forEach(s => {
    const h = s.value * scale;
    g += band(cols[2] + NW / 2, dy, dy + h, cols[3] - NW / 2, s.y0, s.y1, s.color);
    dy += h;
  });
  g += node(cols[0], { ...src[0], label: o.source.label });
  mid.forEach(s => { g += nodeR(cols[1], s); });
  g += `<rect x="${(cols[2] - NW / 2).toFixed(1)}" y="${dst[0].y0.toFixed(1)}" width="${NW}" height="${(dst[0].y1 - dst[0].y0).toFixed(1)}" fill="${PAL.slate}"/>` +
    `<text x="${cols[2]}" y="${(dst[0].y1 + 16).toFixed(1)}" text-anchor="middle" font-size="11.5" fill="${PAL.muted}">downstream</text>`;
  snk.forEach(s => { g += nodeR(cols[3], s); });
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block">${g}</svg>`;
}
