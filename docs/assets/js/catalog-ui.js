/** Catalog selects, claim card, guided demos, custom templates. */

import { HARD_LIMIT_CAP, SOFT_LIMIT_WARN, TEMPLATES } from "./config.js";
import {
  applyModulusColors,
  paintStripLegendOnly,
  renderModulusAnalysis,
  setupModulusUi,
} from "./modulus.js";
import { updateShareUrl } from "./share.js";
import { el, getCatalog, state } from "./state.js";
import { escapeHtml } from "./util.js";

export function predicatesForGroup(groupId) {
  const catalog = getCatalog();
  if (!groupId || groupId === "all") return catalog.predicates;
  return catalog.predicates.filter((p) => p.group === groupId);
}

export function getSelectedPredicate() {
  return getCatalog().byId[el.predicate.value] || null;
}

export function fillGroups() {
  el.group.innerHTML = "";
  const all = document.createElement("option");
  all.value = "all";
  all.textContent = "All families";
  el.group.appendChild(all);
  for (const g of getCatalog().groups) {
    const opt = document.createElement("option");
    opt.value = g.id;
    opt.textContent = g.label;
    el.group.appendChild(opt);
  }
}

export function fillPredicates() {
  const list = predicatesForGroup(el.group.value);
  const prev = el.predicate.value;
  el.predicate.innerHTML = "";
  for (const p of list) {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.title;
    el.predicate.appendChild(opt);
  }
  if (list.some((p) => p.id === prev)) {
    el.predicate.value = prev;
  } else if (list.length) {
    el.predicate.value = list[0].id;
  }
  updateClaimCard();
}

export function updateClaimCard() {
  const p = getSelectedPredicate();
  if (!p || el.useCustom.checked) {
    if (el.useCustom.checked) {
      el.claimCard.hidden = false;
      el.claimTitle.textContent = "Custom predicate";
      el.claimExpected.textContent = "custom";
      el.claimExpected.className = "badge";
      el.claimFormula.textContent = "def predicate(F) -> bool";
      el.claimBlurb.textContent =
        "Your code runs with FieldFactory F (prime, precision, t, constant, …) and helpers from ake_scanner.";
      el.claimSource.textContent = "playground · in-browser only";
    } else {
      el.claimCard.hidden = true;
    }
    return;
  }
  el.claimCard.hidden = false;
  el.claimTitle.textContent = p.title;
  el.claimExpected.textContent = p.expected;
  el.claimExpected.className = `badge pattern-${p.expected}`;
  el.claimFormula.textContent = p.formula;
  el.claimBlurb.textContent = p.blurb;
  el.claimSource.textContent = `examples/${p.module}.py · ${p.function}`;
}

export function applyPredicateDefaults(p, { runLimits = true } = {}) {
  if (!p) return;
  if (runLimits) {
    el.limit.value = String(p.defaultLimit ?? 50);
    el.precision.value = String(p.defaultPrecision ?? 20);
  }
  if (p.modulusHint && el.modulusLens.checked) {
    state.modulusMode = p.modulusHint;
  }
  updateLimitHint();
}

export function updateLimitHint() {
  const lim = Number(el.limit.value) || 0;
  el.limitHint.hidden = lim <= SOFT_LIMIT_WARN;
  if (lim > HARD_LIMIT_CAP) {
    /* capped at run time */
  }
}

export function buildGuided(runScan) {
  el.guided.innerHTML = "";
  for (const g of getCatalog().guided) {
    const p = getCatalog().byId[g.id];
    if (!p) continue;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "guided-card";
    btn.innerHTML = `
      <span class="g-label">${escapeHtml(g.label)}</span>
      <span class="g-teaser">${escapeHtml(g.teaser)}</span>
      <span class="g-run">Run this →</span>
    `;
    btn.addEventListener("click", () => {
      el.useCustom.checked = false;
      el.group.value = "all";
      fillPredicates();
      el.predicate.value = p.id;
      updateClaimCard();
      applyPredicateDefaults(p);
      el.start.value = "2";
      if (p.expected === "mixed") {
        el.modulusLens.checked = true;
        state.modulusMode = p.modulusHint || 4;
      }
      updateShareUrl();
      runScan();
    });
    el.guided.appendChild(btn);
  }
}

export function setupTemplates() {
  el.templateRow.innerHTML = "";
  for (const [, t] of Object.entries(TEMPLATES)) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = t.label;
    btn.addEventListener("click", () => {
      el.customCode.value = t.code;
      el.useCustom.checked = true;
      el.customDrawer.open = true;
      updateClaimCard();
      updateShareUrl();
      el.templateRow.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
    });
    el.templateRow.appendChild(btn);
  }
  if (!el.customCode.value.trim()) {
    el.customCode.value = TEMPLATES.unit_square.code;
  }
}

export function wireForm(runScan) {
  el.group.addEventListener("change", () => {
    fillPredicates();
    updateShareUrl();
  });
  el.predicate.addEventListener("change", () => {
    el.useCustom.checked = false;
    updateClaimCard();
    applyPredicateDefaults(getSelectedPredicate());
    updateShareUrl();
  });
  el.limit.addEventListener("input", () => {
    updateLimitHint();
    updateShareUrl();
  });
  el.start.addEventListener("input", updateShareUrl);
  el.precision.addEventListener("input", updateShareUrl);
  el.verbose.addEventListener("change", updateShareUrl);
  el.useCustom.addEventListener("change", () => {
    if (el.useCustom.checked) el.customDrawer.open = true;
    updateClaimCard();
    updateShareUrl();
  });
  el.customCode.addEventListener("input", updateShareUrl);
  el.modulusLens.addEventListener("change", () => {
    if (!el.modulusLens.checked) {
      state.modulusMode = null;
      if (state.lastResults) {
        applyModulusColors();
        setupModulusUi(state.lastResults);
        paintStripLegendOnly();
        renderModulusAnalysis(state.lastResults);
      }
    } else {
      const p = getSelectedPredicate();
      state.modulusMode = (p && p.modulusHint) || state.suggestedModulus || 4;
      if (state.lastResults) {
        applyModulusColors();
        setupModulusUi(state.lastResults);
        paintStripLegendOnly();
        renderModulusAnalysis(state.lastResults);
      }
    }
    updateShareUrl();
  });
  el.form.addEventListener("submit", (e) => {
    e.preventDefault();
    runScan();
  });
}
