/** Run a catalog or custom scan end-to-end. */

import { HARD_LIMIT_CAP } from "./config.js";
import {
  applyPredicateDefaults,
  getSelectedPredicate,
  updateClaimCard,
} from "./catalog-ui.js";
import { beginLiveStrip, hideProgress, setProgress } from "./progress.js";
import { buildStory, cliCommand, paintStrip } from "./results.js";
import { runEngineScan } from "./runtime.js";
import { updateShareUrl } from "./share.js";
import { el, getCatalog, setStatus, state } from "./state.js";

export async function runScan() {
  if (!state.pyReady) {
    setStatus("Python runtime not ready yet.", "error");
    return;
  }
  if (state.scanning) return;

  const useCustom = el.useCustom.checked;
  let pred = getSelectedPredicate();

  if (useCustom) {
    const code = el.customCode.value.trim();
    if (!code) {
      setStatus("Custom code is empty — paste a predicate or pick a template.", "error");
      el.customDrawer.open = true;
      return;
    }
    pred = {
      id: "custom",
      title: "Custom predicate",
      expected: "custom",
      formula: "def predicate(F) -> bool",
      module: null,
      function: "predicate",
    };
  } else if (!pred) {
    setStatus("Pick a sentence first.", "error");
    return;
  }

  let start = Math.max(2, Number(el.start.value) || 2);
  let limit = Number(el.limit.value) || 50;
  let precision = Number(el.precision.value) || 20;
  const verbose = el.verbose.checked;

  if (limit > HARD_LIMIT_CAP) {
    limit = HARD_LIMIT_CAP;
    el.limit.value = String(HARD_LIMIT_CAP);
  }
  if (limit < start) {
    setStatus("Limit must be ≥ start.", "error");
    return;
  }
  if (precision < 4) precision = 4;
  if (precision > 80) precision = 80;

  state.lastPredicate = pred;
  state.lastWasCustom = useCustom;
  if (el.modulusLens.checked && pred.modulusHint) {
    state.modulusMode = pred.modulusHint;
  }
  if (!el.modulusLens.checked) {
    state.modulusMode = null;
  }

  state.scanning = true;
  el.runBtn.disabled = true;
  el.runBtn.textContent = "Scanning…";
  setStatus(
    `Scanning primes from ${start} to ${limit} (precision ${precision})…`,
    "busy"
  );
  beginLiveStrip();
  setProgress(0, 1, start, "…");
  el.progressLabel.textContent = "Starting scan…";

  try {
    const data = await runEngineScan({
      mode: useCustom ? "custom" : "catalog",
      module: pred.module,
      functionName: pred.function,
      customCode: useCustom ? el.customCode.value : "",
      start,
      limit,
      precision,
      verbose,
    });

    state.lastResults = data.results;
    state.lastReport = data.report;

    const pattern = (data.results.asymptotic || {}).pattern;
    if (pattern === "mixed" && !el.modulusLens.checked) {
      el.modulusLens.checked = true;
    }

    buildStory(data.results, pred);
    paintStrip(data.results, { animate: false });

    el.cliReport.textContent = data.report;
    el.jsonReport.textContent = JSON.stringify(data.results, null, 2);
    el.cliCmd.textContent = cliCommand(pred, start, limit, precision, verbose);
    updateShareUrl();

    const a = data.results.asymptotic || {};
    setStatus(
      `Done · ${a.pattern || "?"} · pass ${data.results.verified_count} / fail ${data.results.failed_count} / err ${data.results.error_count}`
    );

    el.results.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    console.error(err);
    setStatus(`Scan failed: ${String(err.message || err)}`, "error");
  } finally {
    state.scanning = false;
    hideProgress();
    state.liveStrip = null;
    el.runBtn.disabled = !state.pyReady;
    el.runBtn.textContent = "Run scan";
  }
}

export async function maybeAutorunOrSmoke() {
  const params = new URLSearchParams(window.location.search);
  const smoke = params.get("smoke") === "1";
  const autorun = params.get("autorun") === "1" || params.get("run") === "1";

  const waitReady = async () => {
    const deadline = Date.now() + 120000;
    while (!state.pyReady && Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 200));
    }
    if (!state.pyReady) throw new Error("Pyodide not ready");
  };

  if (smoke) {
    const started = Date.now();
    try {
      await waitReady();
      el.useCustom.checked = false;
      el.predicate.value = "one_plus_t_is_square";
      updateClaimCard();
      applyPredicateDefaults(getCatalog().byId.one_plus_t_is_square);
      el.limit.value = "30";
      await runScan();
      const pattern =
        (state.lastResults &&
          state.lastResults.asymptotic &&
          state.lastResults.asymptotic.pattern) ||
        "?";
      const ok = pattern === "eventually_true";
      document.documentElement.dataset.smoke = ok ? "pass" : "fail";
      document.documentElement.dataset.smokePattern = pattern;
      document.title = ok
        ? `SMOKE_PASS ${pattern} ${Date.now() - started}ms`
        : `SMOKE_FAIL ${pattern}`;
      console.log("AKE_SMOKE", document.title);
    } catch (err) {
      document.documentElement.dataset.smoke = "fail";
      document.title = `SMOKE_FAIL ${err.message || err}`;
      console.error("AKE_SMOKE", err);
    }
    return;
  }

  if (autorun) {
    try {
      await waitReady();
      await runScan();
    } catch (err) {
      console.error(err);
      setStatus(`Autorun failed: ${err.message || err}`, "error");
    }
  }
}
