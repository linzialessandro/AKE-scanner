/**
 * AKE Scanner lab — Pyodide worker host + prime-strip UI.
 * Lab 2.0 + power-user: share URLs, auto modulus, custom playground,
 * Web Worker scans, higher limits, live progress, export.
 */
(function () {
  "use strict";

  const PY_FILES = [
    "ake_scanner/__init__.py",
    "ake_scanner/__main__.py",
    "ake_scanner/cli.py",
    "ake_scanner/algebra/__init__.py",
    "ake_scanner/algebra/laurent.py",
    "ake_scanner/algebra/hensel.py",
    "ake_scanner/logic/__init__.py",
    "ake_scanner/logic/scanner.py",
    "examples/demo_hensel.py",
    "examples/advanced_sentences.py",
  ];

  const HARD_LIMIT_CAP = 1000;
  const SOFT_LIMIT_WARN = 200;
  const PYODIDE_VERSION = "0.27.5";
  const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
  const MODULUS_CANDIDATES = [3, 4, 5, 8, 12];

  const TEMPLATES = {
    unit_square: {
      label: "Unit is square",
      code: `from ake_scanner.algebra.hensel import solve_x_n_equals

def predicate(F):
    """∃x  x² = 1 + t  (eventually true; exceptional p=2)."""
    return solve_x_n_equals(F.constant(1) + F.t, 2, F.precision) is not None
`,
    },
    minus_one: {
      label: "−1 is square",
      code: `from ake_scanner.algebra.hensel import is_quadratic_residue

def predicate(F):
    """∃a∈F_p  a² = −1  (mixed: p=2 or p≡1 mod 4)."""
    if F.prime == 2:
        return True
    return is_quadratic_residue(-1, F.prime)
`,
    },
    odd_val: {
      label: "Odd valuation",
      code: `from ake_scanner.algebra.hensel import solve_x_n_equals

def predicate(F):
    """∃x  x² = t  (always false: v(t)=1 is odd)."""
    return solve_x_n_equals(F.t, 2, F.precision) is not None
`,
    },
  };

  const catalog = window.AKE_CATALOG;
  if (!catalog) {
    throw new Error("catalog.js failed to load");
  }

  /** @type {Worker | null} */
  let worker = null;
  /** @type {any} main-thread Pyodide fallback */
  let pyodideMain = null;
  /** "worker" | "main" | null */
  let runtimeMode = null;
  let pyReady = false;
  let packageVersion = "";
  let scanning = false;
  let scanRequestId = 0;
  /** @type {((value: any) => void) | null} */
  let scanResolve = null;
  /** @type {((reason?: any) => void) | null} */
  let scanReject = null;
  let lastResults = null;
  let lastReport = "";
  /** @type {object | null} catalog entry or synthetic custom descriptor */
  let lastPredicate = null;
  let lastWasCustom = false;
  let stripAnimToken = 0;
  let modulusMode = null; // null | number
  let suggestedModulus = null;
  /** Live strip state during progressive scan */
  let liveStrip = null;

  const el = {
    group: document.getElementById("group-select"),
    predicate: document.getElementById("predicate-select"),
    claimCard: document.getElementById("claim-card"),
    claimTitle: document.getElementById("claim-title"),
    claimExpected: document.getElementById("claim-expected"),
    claimFormula: document.getElementById("claim-formula"),
    claimBlurb: document.getElementById("claim-blurb"),
    claimSource: document.getElementById("claim-source"),
    start: document.getElementById("start-input"),
    limit: document.getElementById("limit-input"),
    precision: document.getElementById("precision-input"),
    verbose: document.getElementById("verbose-input"),
    modulusLens: document.getElementById("modulus-lens"),
    limitHint: document.getElementById("limit-hint"),
    form: document.getElementById("scan-form"),
    runBtn: document.getElementById("run-btn"),
    shareBtn: document.getElementById("share-btn"),
    status: document.getElementById("status"),
    progressBlock: document.getElementById("progress-block"),
    progressLabel: document.getElementById("progress-label"),
    progressCounts: document.getElementById("progress-counts"),
    progressFill: document.getElementById("progress-fill"),
    guided: document.getElementById("guided-grid"),
    results: document.getElementById("results"),
    exportTxt: document.getElementById("export-txt"),
    exportJson: document.getElementById("export-json"),
    exportCsv: document.getElementById("export-csv"),
    observedBadge: document.getElementById("observed-badge"),
    expectedBadge: document.getElementById("expected-badge"),
    matchBadge: document.getElementById("match-badge"),
    storyText: document.getElementById("story-text"),
    storyFacts: document.getElementById("story-facts"),
    primeStrip: document.getElementById("prime-strip"),
    thresholdNote: document.getElementById("threshold-note"),
    modulusControls: document.getElementById("modulus-controls"),
    modBtns: document.getElementById("mod-btns"),
    stripLegend: document.getElementById("strip-legend"),
    modulusAnalysis: document.getElementById("modulus-analysis"),
    modulusSuggest: document.getElementById("modulus-suggest"),
    histBody: document.getElementById("hist-body"),
    histBars: document.getElementById("hist-bars"),
    cliCmd: document.getElementById("cli-cmd"),
    shareUrl: document.getElementById("share-url"),
    cliReport: document.getElementById("cli-report"),
    jsonReport: document.getElementById("json-report"),
    customCode: document.getElementById("custom-code"),
    useCustom: document.getElementById("use-custom"),
    customDrawer: document.getElementById("custom-drawer"),
    templateRow: document.getElementById("template-row"),
  };

  function setStatus(msg, kind) {
    el.status.textContent = msg;
    el.status.classList.remove("busy", "error");
    if (kind) el.status.classList.add(kind);
  }

  function assetUrl(rel) {
    return new URL(rel, window.location.href).href;
  }

  function predicatesForGroup(groupId) {
    if (!groupId || groupId === "all") return catalog.predicates;
    return catalog.predicates.filter((p) => p.group === groupId);
  }

  function getSelectedPredicate() {
    return catalog.byId[el.predicate.value] || null;
  }

  function fillGroups() {
    el.group.innerHTML = "";
    const all = document.createElement("option");
    all.value = "all";
    all.textContent = "All families";
    el.group.appendChild(all);
    for (const g of catalog.groups) {
      const opt = document.createElement("option");
      opt.value = g.id;
      opt.textContent = g.label;
      el.group.appendChild(opt);
    }
  }

  function fillPredicates() {
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

  function updateClaimCard() {
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

  function applyPredicateDefaults(p, { runLimits = true } = {}) {
    if (!p) return;
    if (runLimits) {
      el.limit.value = String(p.defaultLimit ?? 50);
      el.precision.value = String(p.defaultPrecision ?? 20);
    }
    if (p.modulusHint && el.modulusLens.checked) {
      modulusMode = p.modulusHint;
    }
    updateLimitHint();
  }

  function updateLimitHint() {
    const lim = Number(el.limit.value) || 0;
    el.limitHint.hidden = lim <= SOFT_LIMIT_WARN;
  }

  function buildGuided() {
    el.guided.innerHTML = "";
    for (const g of catalog.guided) {
      const p = catalog.byId[g.id];
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
          modulusMode = p.modulusHint || 4;
        }
        updateShareUrl();
        runScan();
      });
      el.guided.appendChild(btn);
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // --- Shareable URLs ---

  function readQueryState() {
    const params = new URLSearchParams(window.location.search);
    return {
      p: params.get("p") || params.get("predicate"),
      group: params.get("g") || params.get("group"),
      start: params.get("s") || params.get("start"),
      limit: params.get("l") || params.get("limit"),
      precision: params.get("prec") || params.get("precision"),
      verbose: params.get("v") === "1" || params.get("verbose") === "1",
      mod: params.get("mod"),
      lens: params.get("lens") === "1",
      custom: params.get("custom") === "1",
      autorun: params.get("autorun") === "1" || params.get("run") === "1",
      smoke: params.get("smoke") === "1",
      // code is optional base64url of custom source
      code: params.get("code"),
    };
  }

  function applyQueryState(q) {
    if (q.group && [...el.group.options].some((o) => o.value === q.group)) {
      el.group.value = q.group;
      fillPredicates();
    }
    if (q.p && catalog.byId[q.p]) {
      // ensure visible in select
      const pred = catalog.byId[q.p];
      if (el.group.value !== "all" && pred.group !== el.group.value) {
        el.group.value = "all";
        fillPredicates();
      }
      if ([...el.predicate.options].some((o) => o.value === q.p)) {
        el.predicate.value = q.p;
      }
      updateClaimCard();
      applyPredicateDefaults(pred, { runLimits: !(q.limit || q.precision) });
    }
    if (q.start) el.start.value = String(Math.max(2, parseInt(q.start, 10) || 2));
    if (q.limit) el.limit.value = String(Math.min(HARD_LIMIT_CAP, Math.max(2, parseInt(q.limit, 10) || 50)));
    if (q.precision) {
      el.precision.value = String(Math.min(80, Math.max(4, parseInt(q.precision, 10) || 20)));
    }
    el.verbose.checked = !!q.verbose;
    if (q.lens || q.mod) el.modulusLens.checked = true;
    if (q.mod) {
      const m = parseInt(q.mod, 10);
      if (m > 1) modulusMode = m;
    }
    if (q.custom) {
      el.useCustom.checked = true;
      el.customDrawer.open = true;
    }
    if (q.code) {
      try {
        el.customCode.value = b64urlDecode(q.code);
        el.useCustom.checked = true;
        el.customDrawer.open = true;
      } catch (_) {
        /* ignore bad code param */
      }
    }
    updateClaimCard();
    updateLimitHint();
  }

  function buildShareParams({ includeCode = false } = {}) {
    const params = new URLSearchParams();
    if (el.useCustom.checked) {
      params.set("custom", "1");
      if (includeCode && el.customCode.value.trim()) {
        // Keep links reasonable; skip huge blobs
        const encoded = b64urlEncode(el.customCode.value);
        if (encoded.length < 1800) params.set("code", encoded);
      }
    } else {
      const pred = getSelectedPredicate();
      if (pred) params.set("p", pred.id);
      if (el.group.value && el.group.value !== "all") params.set("g", el.group.value);
    }
    const start = Number(el.start.value) || 2;
    const limit = Number(el.limit.value) || 50;
    const precision = Number(el.precision.value) || 20;
    if (start !== 2) params.set("s", String(start));
    params.set("l", String(limit));
    if (precision !== 20) params.set("prec", String(precision));
    if (el.verbose.checked) params.set("v", "1");
    if (el.modulusLens.checked) params.set("lens", "1");
    if (modulusMode != null) params.set("mod", String(modulusMode));
    params.set("autorun", "1");
    return params;
  }

  function updateShareUrl() {
    if (!el.shareUrl) return;
    const params = buildShareParams({ includeCode: el.useCustom.checked });
    const url = new URL(window.location.href);
    url.search = params.toString();
    el.shareUrl.textContent = url.toString();
  }

  function b64urlEncode(str) {
    const bytes = new TextEncoder().encode(str);
    let bin = "";
    bytes.forEach((b) => {
      bin += String.fromCharCode(b);
    });
    return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function b64urlDecode(str) {
    const pad = str.length % 4 === 0 ? "" : "=".repeat(4 - (str.length % 4));
    const b64 = str.replace(/-/g, "+").replace(/_/g, "/") + pad;
    const bin = atob(b64);
    const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  }

  async function copyShareLink() {
    updateShareUrl();
    const text = el.shareUrl.textContent || "";
    try {
      await navigator.clipboard.writeText(text);
      const old = el.shareBtn.textContent;
      el.shareBtn.textContent = "Link copied";
      setTimeout(() => {
        el.shareBtn.textContent = old;
      }, 1200);
    } catch (_) {
      setStatus("Could not copy link — use the Shareable link field below.", "error");
    }
  }

  // --- Pyodide: Web Worker (preferred) + main-thread fallback ---

  function pageBaseUrl() {
    const u = new URL(window.location.href);
    u.hash = "";
    u.search = "";
    let path = u.pathname;
    if (!path.endsWith("/")) {
      path = path.replace(/\/[^/]*$/, "/");
    }
    u.pathname = path;
    return u.href;
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error(`Could not load ${src}`));
      document.head.appendChild(s);
    });
  }

  async function loadVendorIntoMain(pyodide) {
    const base = pageBaseUrl();
    for (const rel of PY_FILES) {
      const res = await fetch(base + "py/" + rel);
      if (!res.ok) throw new Error(`Failed to fetch py/${rel} (${res.status})`);
      const text = await res.text();
      const fsPath = "/ake_pkg/" + rel;
      const parts = fsPath.split("/").filter(Boolean);
      let cur = "";
      for (let i = 0; i < parts.length - 1; i++) {
        cur += "/" + parts[i];
        try {
          pyodide.FS.mkdir(cur);
        } catch (_) {
          /* exists */
        }
      }
      pyodide.FS.writeFile(fsPath, text);
    }
    pyodide.runPython(`
import sys
if "/ake_pkg" not in sys.path:
    sys.path.insert(0, "/ake_pkg")
if "/ake_pkg/examples" not in sys.path:
    sys.path.insert(0, "/ake_pkg/examples")
from ake_scanner import __version__
from ake_scanner.logic.scanner import scan_primes, results_to_jsonable
from ake_scanner.cli import format_text_report
`);
  }

  async function initMainThread() {
    setStatus("Loading Python on main thread (fallback)…", "busy");
    el.runBtn.disabled = true;
    el.runBtn.textContent = "Loading Python…";
    await loadScript(PYODIDE_CDN + "pyodide.js");
    // eslint-disable-next-line no-undef
    pyodideMain = await loadPyodide({ indexURL: PYODIDE_CDN });
    await loadVendorIntoMain(pyodideMain);
    packageVersion = String(
      pyodideMain.runPython("from ake_scanner import __version__; __version__")
    );
    runtimeMode = "main";
    pyReady = true;
    el.runBtn.disabled = false;
    el.runBtn.textContent = "Run scan";
    setStatus(`Ready · ake-scanner ${packageVersion} · main thread`);
    return true;
  }

  function tryInitWorker(timeoutMs) {
    return new Promise((resolve) => {
      let settled = false;
      const finish = (ok, err) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve({ ok, err });
      };
      const timer = setTimeout(() => {
        finish(false, new Error("Worker init timed out"));
      }, timeoutMs);

      try {
        setStatus("Loading Python worker (Pyodide)…", "busy");
        el.runBtn.disabled = true;
        el.runBtn.textContent = "Loading Python…";

        worker = new Worker(assetUrl("assets/worker.js"));
        const onReady = (ev) => {
          const msg = ev.data || {};
          if (msg.type === "log") {
            console.log("[ake-worker]", msg.message);
            return;
          }
          if (msg.type === "ready") {
            packageVersion = msg.version || "";
            runtimeMode = "worker";
            pyReady = true;
            el.runBtn.disabled = false;
            el.runBtn.textContent = "Run scan";
            setStatus(`Ready · ake-scanner ${packageVersion} · worker`);
            worker.removeEventListener("message", onReady);
            finish(true);
          } else if (msg.type === "error" && !pyReady) {
            worker.removeEventListener("message", onReady);
            finish(false, new Error(msg.message || "Worker init failed"));
          }
        };
        worker.addEventListener("message", onReady);
        worker.addEventListener("message", onWorkerMessage);
        worker.onerror = (err) => {
          console.error(err);
          finish(false, new Error(err.message || "Worker error"));
        };
        worker.postMessage({
          type: "init",
          baseUrl: pageBaseUrl(),
          pyodideCdn: PYODIDE_CDN,
          pyFiles: PY_FILES,
        });
      } catch (err) {
        finish(false, err);
      }
    });
  }

  async function initRuntime() {
    try {
      const w = await tryInitWorker(45000);
      if (w.ok) return true;
      console.warn("Worker unavailable, falling back to main thread:", w.err);
      if (worker) {
        try {
          worker.terminate();
        } catch (_) {
          /* ignore */
        }
        worker = null;
      }
      return await initMainThread();
    } catch (err) {
      console.error(err);
      el.runBtn.disabled = true;
      el.runBtn.textContent = "Unavailable";
      setStatus(`Failed to load Python runtime: ${err.message || err}`, "error");
      return false;
    }
  }

  function onWorkerMessage(ev) {
    const msg = ev.data || {};
    if (msg.type === "log") {
      console.log("[ake-worker]", msg.message);
      return;
    }
    if (msg.type === "progress" && msg.requestId === scanRequestId) {
      handleProgress(msg);
      return;
    }
    if (msg.type === "result" && msg.requestId === scanRequestId) {
      if (scanResolve) {
        const r = scanResolve;
        scanResolve = null;
        scanReject = null;
        r({ results: msg.results, report: msg.report });
      }
      return;
    }
    if (msg.type === "error" && msg.requestId === scanRequestId) {
      if (scanReject) {
        const r = scanReject;
        scanResolve = null;
        scanReject = null;
        r(new Error(msg.message || "Scan failed"));
      }
      return;
    }
  }

  function workerScan(payload) {
    return new Promise((resolve, reject) => {
      if (!worker || !pyReady) {
        reject(new Error("Worker not ready"));
        return;
      }
      scanRequestId += 1;
      const requestId = scanRequestId;
      scanResolve = resolve;
      scanReject = reject;
      worker.postMessage({ type: "scan", requestId, ...payload });
    });
  }

  async function mainThreadScan(payload) {
    const py = pyodideMain;
    if (!py) throw new Error("Main-thread Pyodide not ready");

    // Progress bridge: yield to UI every prime
    const requestId = ++scanRequestId;
    py.globals.set("_ake_progress", (done, total, p, status) => {
      handleProgress({
        requestId,
        done: Number(done),
        total: Number(total),
        p: Number(p),
        status: String(status),
      });
    });

    if (payload.mode === "custom") {
      py.FS.writeFile("/ake_pkg/examples/_user_predicate.py", payload.customCode || "");
    }

    const code = `
import importlib
import json
import sys
from ake_scanner.logic.scanner import scan_primes, results_to_jsonable
from ake_scanner.cli import format_text_report

def _on_progress(done, total, p, status):
    _ake_progress(done, total, p, status)

mode = ${JSON.stringify(payload.mode)}
if mode == "custom":
    if "_user_predicate" in sys.modules:
        del sys.modules["_user_predicate"]
    mod = importlib.import_module("_user_predicate")
    fn = None
    if hasattr(mod, "predicate") and callable(mod.predicate):
        fn = mod.predicate
    else:
        for name in sorted(dir(mod)):
            if name.startswith("predicate_") and callable(getattr(mod, name)):
                fn = getattr(mod, name)
                break
    if fn is None:
        raise AttributeError("Define predicate(F) or predicate_*(F) returning bool.")
else:
    mod = importlib.import_module(${JSON.stringify(payload.module || "")})
    fn = getattr(mod, ${JSON.stringify(payload.functionName || "")})

results = scan_primes(
    fn,
    prime_limit=${Number(payload.limit) || 50},
    start=${Number(payload.start) || 2},
    precision=${Number(payload.precision) || 20},
    progress=False,
    on_progress=_on_progress,
)
report = format_text_report(results, verbose=${payload.verbose ? "True" : "False"}, full=False)
payload_out = results_to_jsonable(results)
json.dumps({"report": report, "results": payload_out})
`;
    const raw = await py.runPythonAsync(code);
    const data = JSON.parse(raw);
    return { results: data.results, report: data.report };
  }

  async function runEngineScan(payload) {
    if (runtimeMode === "worker") return workerScan(payload);
    if (runtimeMode === "main") return mainThreadScan(payload);
    throw new Error("Runtime not ready");
  }

  function setProgress(done, total, p, status) {
    if (!el.progressBlock) return;
    el.progressBlock.hidden = false;
    const pct = total ? Math.round((100 * done) / total) : 0;
    el.progressFill.style.width = `${pct}%`;
    el.progressLabel.textContent =
      done < total ? `Scanning p = ${p} (${status})…` : "Finishing report…";
    el.progressCounts.textContent = `${done} / ${total}`;
  }

  function hideProgress() {
    if (!el.progressBlock) return;
    el.progressBlock.hidden = true;
    el.progressFill.style.width = "0%";
  }

  function beginLiveStrip() {
    stripAnimToken += 1;
    el.primeStrip.innerHTML = "";
    liveStrip = { cells: new Map() };
    el.results.hidden = false;
    el.modulusAnalysis.hidden = true;
    el.thresholdNote.textContent = "Live scan — cells appear as each prime finishes.";
  }

  function appendLiveCell(p, status) {
    if (!liveStrip) return;
    if (liveStrip.cells.has(p)) return;
    const cell = document.createElement("button");
    cell.type = "button";
    cell.className = `prime-cell ${status} visible`;
    cell.setAttribute("role", "listitem");
    cell.dataset.prime = String(p);
    cell.dataset.status = status;
    cell.textContent = String(p);
    cell.title = `p=${p} · ${status}`;
    cell.setAttribute("aria-label", `Prime ${p}, ${status}`);
    el.primeStrip.appendChild(cell);
    liveStrip.cells.set(p, cell);
  }

  function handleProgress(msg) {
    const { done, total, p, status } = msg;
    setProgress(done, total, p, status);
    appendLiveCell(p, status);
    setStatus(`Scanning… ${done}/${total} (p=${p})`, "busy");
  }

  // --- Export ---

  function resultsToCsv(results) {
    const statusMap = {};
    for (const p of results.passed_primes || []) statusMap[p] = ["passed", ""];
    for (const p of results.failed_primes || []) statusMap[p] = ["failed", ""];
    for (const p of results.error_primes || []) {
      statusMap[p] = ["error", (results.details && results.details[p]) || ""];
    }
    const lines = ["prime,status,detail"];
    for (const p of results.primes_scanned || []) {
      const [st, detail] = statusMap[p] || ["unknown", ""];
      const d = String(detail).replace(/"/g, '""');
      lines.push(`${p},${st},"${d}"`);
    }
    return lines.join("\n") + "\n";
  }

  function downloadBlob(filename, text, mime) {
    const blob = new Blob([text], { type: mime || "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  function exportBasename() {
    const id = (lastPredicate && lastPredicate.id) || "scan";
    const lim = (lastResults && lastResults.prime_limit) || el.limit.value || "";
    return `ake-${id}-l${lim}`;
  }

  function setupExport() {
    el.exportTxt.addEventListener("click", () => {
      if (!lastReport) {
        setStatus("Nothing to export yet — run a scan first.", "error");
        return;
      }
      downloadBlob(`${exportBasename()}.txt`, lastReport, "text/plain");
    });
    el.exportJson.addEventListener("click", () => {
      if (!lastResults) {
        setStatus("Nothing to export yet — run a scan first.", "error");
        return;
      }
      downloadBlob(
        `${exportBasename()}.json`,
        JSON.stringify(lastResults, null, 2),
        "application/json"
      );
    });
    el.exportCsv.addEventListener("click", () => {
      if (!lastResults) {
        setStatus("Nothing to export yet — run a scan first.", "error");
        return;
      }
      downloadBlob(`${exportBasename()}.csv`, resultsToCsv(lastResults), "text/csv");
    });
  }

  // --- Results UI ---

  function statusForPrime(results, p) {
    if (results.passed_primes.includes(p)) return "pass";
    if (results.failed_primes.includes(p)) return "fail";
    if (results.error_primes.includes(p)) return "error";
    return "pending";
  }

  function buildStory(results, pred) {
    const a = results.asymptotic || {};
    const pattern = a.pattern || "unknown";
    el.observedBadge.textContent = pattern;
    el.observedBadge.className = `badge big pattern-${pattern}`;

    if (pred && pred.expected && pred.expected !== "custom") {
      el.expectedBadge.hidden = false;
      el.expectedBadge.textContent = `expected ${pred.expected}`;
      el.expectedBadge.className = `badge muted pattern-${pred.expected}`;
      const match = pred.expected === pattern;
      el.matchBadge.hidden = false;
      el.matchBadge.textContent = match ? "matches catalog" : "differs from catalog";
      el.matchBadge.className = `badge ${match ? "match" : "mismatch"}`;
    } else {
      el.expectedBadge.hidden = true;
      el.matchBadge.hidden = true;
    }

    const exceptional = a.exceptional_primes || [];
    const threshold = a.threshold;
    const tailCount = a.tail_count || 0;
    const n = a.primes_scanned_count || (results.primes_scanned || []).length;

    const stories = {
      eventually_true: `After a finite mess, φ holds on the clean tail. This is the AKE-shaped signal: evidence that the sentence is true for all sufficiently large primes (in the scanned range).`,
      eventually_false: `After a finite early stretch, φ fails for every larger prime in range — asymptotic failure, not a one-off.`,
      always_true: `φ held for every prime scanned. No exceptional set, no threshold drama — constant truth on this window.`,
      always_false: `φ failed for every prime scanned. Often a structural obstruction (valuation, characteristic, surjectivity).`,
      mixed: `No single threshold N. Truth wobbles with p — look for a congruence (quadratic residue, cyclotomic condition) rather than “large enough p.”`,
      unknown: a.summary || "Pattern could not be classified.",
    };

    el.storyText.textContent = stories[pattern] || stories.unknown;

    const facts = [];
    if (a.summary) facts.push(a.summary);
    if (threshold != null) facts.push(`Threshold N = ${threshold}`);
    else if (pattern === "mixed") facts.push("Threshold N: none (mixed)");
    if (pattern === "eventually_true" || pattern === "eventually_false") {
      facts.push(
        exceptional.length
          ? `Called-out primes: ${exceptional.join(", ")}`
          : "No exceptional primes recorded"
      );
      facts.push(`Tail length: ${tailCount} primes`);
    }
    facts.push(
      `Counts: pass ${results.verified_count} · fail ${results.failed_count} · err ${results.error_count} · total ${n}`
    );
    facts.push(`Precision: ${results.precision}`);

    el.storyFacts.innerHTML = facts.map((f) => `<li>${escapeHtml(f)}</li>`).join("");
  }

  /**
   * Score how well pass/fail separates by residue classes mod m.
   * Higher = more “explained by mod m” (low entropy of pass rate across classes
   * that have samples, with variance between classes).
   */
  function analyzeModulus(results, m) {
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
    // Prefer moduli where some classes are ~0 and others ~1 (high variance)
    // and that use more residue classes with data.
    const score = variance * Math.log(1 + rates.length);
    return { m, bins, score, rates };
  }

  function bestModulus(results) {
    let best = null;
    for (const m of MODULUS_CANDIDATES) {
      const a = analyzeModulus(results, m);
      if (!best || a.score > best.score) best = a;
    }
    return best;
  }

  function renderModulusAnalysis(results) {
    const pattern = (results.asymptotic || {}).pattern;
    const interesting =
      pattern === "mixed" ||
      (lastPredicate && lastPredicate.modulusHint) ||
      el.modulusLens.checked;

    if (!interesting || !(results.primes_scanned || []).length) {
      el.modulusAnalysis.hidden = true;
      suggestedModulus = null;
      return;
    }

    const best = bestModulus(results);
    suggestedModulus = best && best.score > 0.02 ? best.m : null;

    // Prefer catalog hint when present and competitive
    const hint = lastPredicate && lastPredicate.modulusHint;
    const analysisM =
      modulusMode != null
        ? modulusMode
        : hint || suggestedModulus || (best && best.m) || 4;
    const analysis = analyzeModulus(results, analysisM);

    el.modulusAnalysis.hidden = false;

    if (suggestedModulus != null) {
      const s = analyzeModulus(results, suggestedModulus);
      const pure = s.rates.filter((r) => r < 0.05 || r > 0.95).length;
      el.modulusSuggest.innerHTML =
        `Best simple congruence fit among {${MODULUS_CANDIDATES.join(", ")}}: ` +
        `<strong>p mod ${suggestedModulus}</strong>` +
        (pure >= 1
          ? ` — ${pure} residue class(es) nearly pure pass or fail.`
          : ` (score ${s.score.toFixed(3)}).`) +
        (hint && hint !== suggestedModulus
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
      if (suggestedModulus === analysisM && (rate < 0.05 || rate > 0.95) && decided > 0) {
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
        modulusMode = analysisM;
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

    // Auto-enable suggested lens for mixed if user left mod unset
    if (
      pattern === "mixed" &&
      el.modulusLens.checked &&
      modulusMode == null &&
      suggestedModulus != null
    ) {
      modulusMode = suggestedModulus;
    }
  }

  function paintStrip(results, { animate = true } = {}) {
    const primes = results.primes_scanned || [];
    const a = results.asymptotic || {};
    const threshold = a.threshold;
    const tailSet = new Set(a.tail_primes || []);
    const token = ++stripAnimToken;

    el.primeStrip.innerHTML = "";
    const cells = [];

    for (const p of primes) {
      const st = statusForPrime(results, p);
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = `prime-cell ${st}`;
      cell.setAttribute("role", "listitem");
      cell.dataset.prime = String(p);
      cell.dataset.status = st;
      cell.textContent = String(p);
      cell.title = `p=${p} · ${st}`;
      cell.setAttribute("aria-label", `Prime ${p}, ${st}`);
      if (threshold != null && p === threshold) {
        cell.classList.add("threshold-mark");
      }
      if (tailSet.has(p)) {
        cell.classList.add("tail");
      }
      el.primeStrip.appendChild(cell);
      cells.push(cell);
    }

    renderModulusAnalysis(results);
    applyModulusColors();

    const thr =
      threshold != null ? `Threshold marker on p = ${threshold} (dashed). ` : "";
    const tail =
      (a.tail_count || 0) > 0
        ? `Clean/failing tail outlined in blue (${a.tail_count} primes). `
        : "";
    el.thresholdNote.textContent =
      thr +
      tail +
      "Hover a cell for the prime and status. " +
      (modulusMode
        ? `Residue lens: color = p mod ${modulusMode}; inset ring still shows pass/fail.`
        : "");

    setupModulusUi(results);

    if (!animate || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      cells.forEach((c) => c.classList.add("visible"));
      return;
    }

    let i = 0;
    const batch = Math.max(1, Math.ceil(cells.length / 40));
    function step() {
      if (token !== stripAnimToken) return;
      const end = Math.min(i + batch, cells.length);
      for (; i < end; i++) {
        cells[i].classList.add("visible");
      }
      if (i < cells.length) {
        requestAnimationFrame(step);
      }
    }
    requestAnimationFrame(step);
  }

  function setupModulusUi(results) {
    const pred = lastPredicate;
    const pattern = (results.asymptotic || {}).pattern;
    const show =
      pattern === "mixed" ||
      (pred && pred.modulusHint) ||
      el.modulusLens.checked ||
      suggestedModulus != null;

    el.modulusControls.hidden = !show;
    if (!show) {
      return;
    }

    const mods = [...new Set([...MODULUS_CANDIDATES, suggestedModulus, pred && pred.modulusHint].filter(Boolean))];
    const preferred =
      modulusMode != null
        ? modulusMode
        : (pred && pred.modulusHint) || suggestedModulus || 4;
    if (modulusMode == null && el.modulusLens.checked) modulusMode = preferred;

    el.modBtns.innerHTML = "";
    const off = document.createElement("button");
    off.type = "button";
    off.textContent = "off";
    off.className = modulusMode == null ? "active" : "";
    off.addEventListener("click", () => {
      modulusMode = null;
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
      b.textContent = String(m) + (m === suggestedModulus ? "★" : "");
      b.title = m === suggestedModulus ? "Suggested modulus" : `p mod ${m}`;
      b.className = modulusMode === m ? "active" : "";
      b.addEventListener("click", () => {
        modulusMode = m;
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

  function paintStripLegendOnly() {
    if (modulusMode) {
      el.stripLegend.textContent = `Residue lens on: cell color = p mod ${modulusMode}. Inset ring = pass (green) / fail (brick).`;
      el.thresholdNote.textContent = `Color encodes p mod ${modulusMode}. Pass/fail still shown as an inset ring.`;
    } else {
      el.stripLegend.textContent =
        "Each cell is a prime. Green = pass, brick = fail, amber = runtime error.";
    }
  }

  function applyModulusColors() {
    const cells = el.primeStrip.querySelectorAll(".prime-cell");
    cells.forEach((cell) => {
      for (const c of [...cell.classList]) {
        if (c.startsWith("mod-")) cell.classList.remove(c);
      }
      if (modulusMode == null) return;
      const p = Number(cell.dataset.prime);
      const r = ((p % modulusMode) + modulusMode) % modulusMode;
      cell.classList.add("mod-on", `mod-${r % 8}`);
    });
  }

  function cliCommand(pred, start, limit, precision, verbose) {
    if (!pred || pred.id === "custom") {
      return "# custom playground predicate — save to a .py file and run:\n# ake-scan my_pred.py predicate -s … -l …";
    }
    const file = `examples/${pred.module}.py`;
    const parts = [
      "ake-scan",
      file,
      pred.function,
      "-s",
      String(start),
      "-l",
      String(limit),
      "-p",
      String(precision),
    ];
    if (verbose) parts.push("-v");
    else parts.push("-q");
    return parts.join(" ");
  }

  async function runScan() {
    if (!pyReady) {
      setStatus("Python runtime not ready yet.", "error");
      return;
    }
    if (scanning) return;

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

    lastPredicate = pred;
    lastWasCustom = useCustom;
    if (el.modulusLens.checked && pred.modulusHint) {
      modulusMode = pred.modulusHint;
    }
    if (!el.modulusLens.checked) {
      modulusMode = null;
    }

    scanning = true;
    el.runBtn.disabled = true;
    el.runBtn.textContent = "Scanning…";
    setStatus(`Scanning primes from ${start} to ${limit} (precision ${precision})…`, "busy");
    beginLiveStrip();
    setProgress(0, 1, start, "…");
    el.progressLabel.textContent = "Starting worker scan…";

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

      lastResults = data.results;
      lastReport = data.report;

      const pattern = (data.results.asymptotic || {}).pattern;
      if (pattern === "mixed" && !el.modulusLens.checked) {
        el.modulusLens.checked = true;
      }

      buildStory(data.results, pred);
      // Re-paint final strip with threshold/tail markers (cells already visible)
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
      const msg = String(err.message || err);
      setStatus(`Scan failed: ${msg}`, "error");
    } finally {
      scanning = false;
      hideProgress();
      liveStrip = null;
      el.runBtn.disabled = !pyReady;
      el.runBtn.textContent = "Run scan";
    }
  }

  function setupTabs() {
    const tabs = document.querySelectorAll(".tab");
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const name = tab.dataset.tab;
        tabs.forEach((t) => {
          const on = t === tab;
          t.classList.toggle("active", on);
          t.setAttribute("aria-selected", on ? "true" : "false");
        });
        document.querySelectorAll(".tab-panel").forEach((panel) => {
          const on = panel.id === `panel-${name}`;
          panel.hidden = !on;
          panel.classList.toggle("active", on);
        });
      });
    });
  }

  function setupCopyButtons() {
    document.querySelectorAll("[data-copy]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-copy");
        const node = document.getElementById(id);
        if (!node) return;
        const text = node.textContent || "";
        try {
          await navigator.clipboard.writeText(text);
          const old = btn.textContent;
          btn.textContent = "Copied";
          setTimeout(() => {
            btn.textContent = old;
          }, 1200);
        } catch (_) {
          btn.textContent = "Copy failed";
        }
      });
    });
  }

  function setupTemplates() {
    el.templateRow.innerHTML = "";
    for (const [key, t] of Object.entries(TEMPLATES)) {
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
    // Default template in empty editor
    if (!el.customCode.value.trim()) {
      el.customCode.value = TEMPLATES.unit_square.code;
    }
  }

  function wireForm() {
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
        modulusMode = null;
        if (lastResults) {
          applyModulusColors();
          setupModulusUi(lastResults);
          paintStripLegendOnly();
          renderModulusAnalysis(lastResults);
        }
      } else {
        const p = getSelectedPredicate();
        modulusMode = (p && p.modulusHint) || suggestedModulus || 4;
        if (lastResults) {
          applyModulusColors();
          setupModulusUi(lastResults);
          paintStripLegendOnly();
          renderModulusAnalysis(lastResults);
        }
      }
      updateShareUrl();
    });
    el.form.addEventListener("submit", (e) => {
      e.preventDefault();
      runScan();
    });
    el.shareBtn.addEventListener("click", copyShareLink);
  }

  async function maybeAutorunOrSmoke() {
    const q = readQueryState();
    const waitReady = async () => {
      const deadline = Date.now() + 120000;
      while (!pyReady && Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 200));
      }
      if (!pyReady) throw new Error("Pyodide not ready");
    };

    if (q.smoke) {
      const started = Date.now();
      try {
        await waitReady();
        el.useCustom.checked = false;
        el.predicate.value = "one_plus_t_is_square";
        updateClaimCard();
        applyPredicateDefaults(catalog.byId.one_plus_t_is_square);
        el.limit.value = "30";
        await runScan();
        const pattern =
          (lastResults && lastResults.asymptotic && lastResults.asymptotic.pattern) || "?";
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

    if (q.autorun) {
      try {
        await waitReady();
        await runScan();
      } catch (err) {
        console.error(err);
        setStatus(`Autorun failed: ${err.message || err}`, "error");
      }
    }
  }

  function boot() {
    fillGroups();
    fillPredicates();
    setupTemplates();

    // Defaults then query override
    if (catalog.byId.one_plus_t_is_square) {
      el.predicate.value = "one_plus_t_is_square";
      updateClaimCard();
      applyPredicateDefaults(catalog.byId.one_plus_t_is_square);
    }

    const q = readQueryState();
    applyQueryState(q);

    buildGuided();
    setupTabs();
    setupCopyButtons();
    setupExport();
    wireForm();
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
})();
