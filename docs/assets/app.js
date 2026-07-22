/**
 * AKE Scanner lab — entry module.
 * Bootstraps DOM, catalog UI, runtime, and autorun.
 */
import {
  applyPredicateDefaults,
  buildGuided,
  fillGroups,
  fillPredicates,
  setupTemplates,
  updateClaimCard,
  updateLimitHint,
  wireForm,
} from "./js/catalog-ui.js";
import { setupExport } from "./js/export.js";
import { setupCopyButtons, setupTabs } from "./js/results.js";
import { initRuntime } from "./js/runtime.js";
import { maybeAutorunOrSmoke, runScan } from "./js/scan.js";
import {
  applyQueryState,
  copyShareLink,
  readQueryState,
  updateShareUrl,
} from "./js/share.js";
import { bindDom, el, getCatalog } from "./js/state.js";

function boot() {
  bindDom();
  getCatalog();

  fillGroups();
  fillPredicates();
  setupTemplates();

  if (getCatalog().byId.one_plus_t_is_square) {
    el.predicate.value = "one_plus_t_is_square";
    updateClaimCard();
    applyPredicateDefaults(getCatalog().byId.one_plus_t_is_square);
  }

  const q = readQueryState();
  applyQueryState(q, {
    fillPredicates,
    updateClaimCard,
    applyPredicateDefaults,
    updateLimitHint,
  });

  buildGuided(runScan);
  setupTabs();
  setupCopyButtons();
  setupExport();
  wireForm(runScan);
  el.shareBtn.addEventListener("click", copyShareLink);
  updateShareUrl();

  initRuntime().then((ok) => {
    if (ok) maybeAutorunOrSmoke();
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
