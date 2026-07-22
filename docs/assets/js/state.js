/**
 * Shared lab state (mutable singleton).
 * Modules read/write fields; boot() binds DOM refs into `el`.
 */

export const el = {};

export const state = {
  catalog: null,
  worker: null,
  pyodideMain: null,
  /** @type {"worker"|"main"|null} */
  runtimeMode: null,
  pyReady: false,
  packageVersion: "",
  scanning: false,
  scanRequestId: 0,
  scanResolve: null,
  scanReject: null,
  lastResults: null,
  lastReport: "",
  lastPredicate: null,
  lastWasCustom: false,
  stripAnimToken: 0,
  modulusMode: null,
  suggestedModulus: null,
  liveStrip: null,
};

export function bindDom() {
  const ids = {
    group: "group-select",
    predicate: "predicate-select",
    claimCard: "claim-card",
    claimTitle: "claim-title",
    claimExpected: "claim-expected",
    claimFormula: "claim-formula",
    claimBlurb: "claim-blurb",
    claimSource: "claim-source",
    start: "start-input",
    limit: "limit-input",
    precision: "precision-input",
    verbose: "verbose-input",
    modulusLens: "modulus-lens",
    limitHint: "limit-hint",
    form: "scan-form",
    runBtn: "run-btn",
    shareBtn: "share-btn",
    status: "status",
    progressBlock: "progress-block",
    progressLabel: "progress-label",
    progressCounts: "progress-counts",
    progressFill: "progress-fill",
    guided: "guided-grid",
    results: "results",
    exportTxt: "export-txt",
    exportJson: "export-json",
    exportCsv: "export-csv",
    observedBadge: "observed-badge",
    expectedBadge: "expected-badge",
    matchBadge: "match-badge",
    storyText: "story-text",
    storyFacts: "story-facts",
    primeStrip: "prime-strip",
    thresholdNote: "threshold-note",
    explainPanel: "explain-panel",
    explainTitle: "explain-title",
    explainBody: "explain-body",
    explainWitness: "explain-witness",
    modulusControls: "modulus-controls",
    modBtns: "mod-btns",
    stripLegend: "strip-legend",
    modulusAnalysis: "modulus-analysis",
    modulusSuggest: "modulus-suggest",
    histBody: "hist-body",
    histBars: "hist-bars",
    cliCmd: "cli-cmd",
    shareUrl: "share-url",
    cliReport: "cli-report",
    jsonReport: "json-report",
    customCode: "custom-code",
    useCustom: "use-custom",
    customDrawer: "custom-drawer",
    templateRow: "template-row",
  };
  for (const [key, id] of Object.entries(ids)) {
    el[key] = document.getElementById(id);
  }
}

export function setStatus(msg, kind) {
  if (!el.status) return;
  el.status.textContent = msg;
  el.status.classList.remove("busy", "error");
  if (kind) el.status.classList.add(kind);
}

export function getCatalog() {
  if (!state.catalog) {
    state.catalog = window.AKE_CATALOG;
    if (!state.catalog) throw new Error("catalog.js failed to load");
  }
  return state.catalog;
}
