/** Residue-class analysis and strip recoloring. */

import { MODULUS_CANDIDATES } from "./config.js";
import { el, state } from "./state.js";
import { updateShareUrl } from "./share.js";

export function analyzeModulus(results, m) {
  const bins = Array.from({ length: m }, () => ({ pass: 0, fail: 0, err: 0 }));
  const passSet = new Set(results.passed_primes || []);
  const failSet = new Set(results.failed_primes || []);
  const errSet = new Set(results.error_primes || []);

  for (const p of results.primes_scanned || []) {
    const r = ((p % m) + m) % m;
    if (passSet.has(p)) bins[r].pass += 1;
    else if (failSet.has(p)) bins[r].fail += 1;
    else if (errSet.has(p)) bins[r].err += 1;
  }

  const rates = [];
  for (let r = 0; r < m; r++) {
    const t = bins[r].pass + bins[r].fail;
    if (t > 0) rates.push(bins[r].pass / t);
  }
  if (rates.length < 2) {
    return { m, bins, score: -1, rates };
  }
  const mean = rates.reduce((a, b) => a + b, 0) / rates.length;
  const variance = rates.reduce((a, b) => a + (b - mean) ** 2, 0) / rates.length;
  const score = variance * Math.log(1 + rates.length);
  return { m, bins, score, rates };
}

export function bestModulus(results) {
  let best = null;
  for (const m of MODULUS_CANDIDATES) {
    const a = analyzeModulus(results, m);
    if (!best || a.score > best.score) best = a;
  }
  return best;
}

export function applyModulusColors() {
  const cells = el.primeStrip.querySelectorAll(".prime-cell");
  cells.forEach((cell) => {
    for (const c of [...cell.classList]) {
      if (c.startsWith("mod-")) cell.classList.remove(c);
    }
    if (state.modulusMode == null) return;
    const p = Number(cell.dataset.prime);
    const r = ((p % state.modulusMode) + state.modulusMode) % state.modulusMode;
    cell.classList.add("mod-on", `mod-${r % 8}`);
  });
}

export function paintStripLegendOnly() {
  if (state.modulusMode) {
    el.stripLegend.textContent = `Residue lens on: cell color = p mod ${state.modulusMode}. Inset ring = pass (green) / fail (brick).`;
    el.thresholdNote.textContent = `Color encodes p mod ${state.modulusMode}. Pass/fail still shown as an inset ring.`;
  } else {
    el.stripLegend.textContent =
      "Each cell is a prime. Green = pass, brick = fail, amber = runtime error.";
  }
}

export function setupModulusUi(results) {
  const pred = state.lastPredicate;
  const pattern = (results.asymptotic || {}).pattern;
  const show =
    pattern === "mixed" ||
    (pred && pred.modulusHint) ||
    el.modulusLens.checked ||
    state.suggestedModulus != null;

  el.modulusControls.hidden = !show;
  if (!show) return;

  const mods = [
    ...new Set(
      [...MODULUS_CANDIDATES, state.suggestedModulus, pred && pred.modulusHint].filter(
        Boolean
      )
    ),
  ];
  const preferred =
    state.modulusMode != null
      ? state.modulusMode
      : (pred && pred.modulusHint) || state.suggestedModulus || 4;
  if (state.modulusMode == null && el.modulusLens.checked) state.modulusMode = preferred;

  el.modBtns.innerHTML = "";
  const off = document.createElement("button");
  off.type = "button";
  off.textContent = "off";
  off.className = state.modulusMode == null ? "active" : "";
  off.addEventListener("click", () => {
    state.modulusMode = null;
    el.modulusLens.checked = false;
    applyModulusColors();
    setupModulusUi(results);
    paintStripLegendOnly();
    renderModulusAnalysis(results);
    updateShareUrl();
  });
  el.modBtns.appendChild(off);

  for (const m of mods) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = String(m) + (m === state.suggestedModulus ? "★" : "");
    b.title = m === state.suggestedModulus ? "Suggested modulus" : `p mod ${m}`;
    b.className = state.modulusMode === m ? "active" : "";
    b.addEventListener("click", () => {
      state.modulusMode = m;
      el.modulusLens.checked = true;
      applyModulusColors();
      setupModulusUi(results);
      paintStripLegendOnly();
      renderModulusAnalysis(results);
      updateShareUrl();
    });
    el.modBtns.appendChild(b);
  }
}

export function renderModulusAnalysis(results) {
  const pattern = (results.asymptotic || {}).pattern;
  const interesting =
    pattern === "mixed" ||
    (state.lastPredicate && state.lastPredicate.modulusHint) ||
    el.modulusLens.checked;

  if (!interesting || !(results.primes_scanned || []).length) {
    el.modulusAnalysis.hidden = true;
    state.suggestedModulus = null;
    return;
  }

  const best = bestModulus(results);
  state.suggestedModulus = best && best.score > 0.02 ? best.m : null;

  const hint = state.lastPredicate && state.lastPredicate.modulusHint;
  const analysisM =
    state.modulusMode != null
      ? state.modulusMode
      : hint || state.suggestedModulus || (best && best.m) || 4;
  const analysis = analyzeModulus(results, analysisM);

  el.modulusAnalysis.hidden = false;

  if (state.suggestedModulus != null) {
    const s = analyzeModulus(results, state.suggestedModulus);
    const pure = s.rates.filter((r) => r < 0.05 || r > 0.95).length;
    el.modulusSuggest.innerHTML =
      `Best simple congruence fit among {${MODULUS_CANDIDATES.join(", ")}}: ` +
      `<strong>p mod ${state.suggestedModulus}</strong>` +
      (pure >= 1
        ? ` — ${pure} residue class(es) nearly pure pass or fail.`
        : ` (score ${s.score.toFixed(3)}).`) +
      (hint && hint !== state.suggestedModulus
        ? ` Catalog hint was mod ${hint}.`
        : hint
          ? ` Matches catalog hint.`
          : "") +
      ` Showing table for <strong>m = ${analysisM}</strong>.`;
  } else {
    el.modulusSuggest.textContent =
      pattern === "mixed"
        ? `No sharp single-modulus split found in {${MODULUS_CANDIDATES.join(", ")}}. Try a larger limit. Showing m = ${analysisM}.`
        : `Residue breakdown for m = ${analysisM}.`;
  }

  el.histBody.innerHTML = "";
  el.histBars.innerHTML = "";
  for (let r = 0; r < analysisM; r++) {
    const b = analysis.bins[r];
    const tot = b.pass + b.fail + b.err;
    if (tot === 0) continue;
    const decided = b.pass + b.fail;
    const rate = decided ? b.pass / decided : 0;
    const tr = document.createElement("tr");
    if (
      state.suggestedModulus === analysisM &&
      (rate < 0.05 || rate > 0.95) &&
      decided > 0
    ) {
      tr.classList.add("suggested");
    }
    const pct = decided ? `${Math.round(rate * 100)}%` : "—";
    tr.innerHTML = `
      <td><code>${r}</code></td>
      <td>${b.pass}</td>
      <td>${b.fail}</td>
      <td>${b.err}</td>
      <td><span class="rate-bar${rate < 0.5 ? " low" : ""}" style="width:${Math.max(4, rate * 48)}px"></span>${pct}</td>
      <td></td>
    `;
    const applyBtn = document.createElement("button");
    applyBtn.type = "button";
    applyBtn.className = "btn ghost";
    applyBtn.textContent = "lens";
    applyBtn.title = `Color strip by p mod ${analysisM}`;
    applyBtn.addEventListener("click", () => {
      el.modulusLens.checked = true;
      state.modulusMode = analysisM;
      applyModulusColors();
      setupModulusUi(results);
      paintStripLegendOnly();
      updateShareUrl();
    });
    tr.lastElementChild.appendChild(applyBtn);
    el.histBody.appendChild(tr);

    const row = document.createElement("div");
    row.className = "hist-bar-row";
    const passW = tot ? (100 * b.pass) / tot : 0;
    const failW = tot ? (100 * b.fail) / tot : 0;
    row.innerHTML = `
      <span>≡${r}</span>
      <div class="hist-bar-track">
        <div class="hist-bar-pass" style="width:${passW}%"></div>
        <div class="hist-bar-fail" style="width:${failW}%"></div>
      </div>
      <span>${b.pass}/${tot}</span>
    `;
    el.histBars.appendChild(row);
  }

  if (
    pattern === "mixed" &&
    el.modulusLens.checked &&
    state.modulusMode == null &&
    state.suggestedModulus != null
  ) {
    state.modulusMode = state.suggestedModulus;
  }
}
