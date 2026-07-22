/**
 * AKE Scanner lab — Pyodide host + prime-strip UI.
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

  const HARD_LIMIT_CAP = 200;
  const SOFT_LIMIT_WARN = 80;
  const PYODIDE_VERSION = "0.27.5";
  const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

  const catalog = window.AKE_CATALOG;
  if (!catalog) {
    throw new Error("catalog.js failed to load");
  }

  /** @type {import('pyodide').PyodideInterface | null} */
  let pyodide = null;
  let pyReady = false;
  let scanning = false;
  let lastResults = null;
  let lastPredicate = null;
  let stripAnimToken = 0;
  let modulusMode = null; // null | number

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
    status: document.getElementById("status"),
    guided: document.getElementById("guided-grid"),
    results: document.getElementById("results"),
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
    cliCmd: document.getElementById("cli-cmd"),
    cliReport: document.getElementById("cli-report"),
    jsonReport: document.getElementById("json-report"),
  };

  function setStatus(msg, kind) {
    el.status.textContent = msg;
    el.status.classList.remove("busy", "error");
    if (kind) el.status.classList.add(kind);
  }

  function assetUrl(rel) {
    // Resolve relative to this page (works on project Pages under /AKE-scanner/)
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
    if (!p) {
      el.claimCard.hidden = true;
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

  async function ensureDirs(path) {
    const parts = path.split("/").filter(Boolean);
    let cur = "";
    for (let i = 0; i < parts.length - 1; i++) {
      cur += "/" + parts[i];
      try {
        pyodide.FS.mkdir(cur);
      } catch (_) {
        /* exists */
      }
    }
  }

  async function loadVendorIntoFs() {
    setStatus("Fetching Python package…", "busy");
    for (const rel of PY_FILES) {
      const url = assetUrl(`py/${rel}`);
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Failed to fetch py/${rel} (${res.status})`);
      }
      const text = await res.text();
      const fsPath = `/ake_pkg/${rel}`;
      await ensureDirs(fsPath);
      pyodide.FS.writeFile(fsPath, text);
    }
    pyodide.runPython(`
import sys
if "/ake_pkg" not in sys.path:
    sys.path.insert(0, "/ake_pkg")
if "/ake_pkg/examples" not in sys.path:
    sys.path.insert(0, "/ake_pkg/examples")
`);
  }

  async function initPyodide() {
    try {
      setStatus("Loading Pyodide (Python in WASM)…", "busy");
      el.runBtn.disabled = true;
      el.runBtn.textContent = "Loading Python…";

      await loadScript(`${PYODIDE_CDN}pyodide.js`);
      // eslint-disable-next-line no-undef
      pyodide = await loadPyodide({ indexURL: PYODIDE_CDN });
      await loadVendorIntoFs();

      // Smoke import
      pyodide.runPython(`
from ake_scanner import __version__
from ake_scanner.logic.scanner import scan_primes
from ake_scanner.cli import format_text_report
from ake_scanner.logic.scanner import results_to_jsonable
`);

      pyReady = true;
      el.runBtn.disabled = false;
      el.runBtn.textContent = "Run scan";
      setStatus(`Ready · ake-scanner ${pyodide.runPython("from ake_scanner import __version__; __version__")}`);
      return true;
    } catch (err) {
      console.error(err);
      el.runBtn.disabled = true;
      el.runBtn.textContent = "Unavailable";
      setStatus(`Failed to load Python runtime: ${err.message || err}`, "error");
      return false;
    }
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

    if (pred && pred.expected) {
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

    applyModulusColors();

    const thr =
      threshold != null
        ? `Threshold marker on p = ${threshold} (dashed). `
        : "";
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

    // Setup modulus UI
    setupModulusUi(results);

    if (!animate || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      cells.forEach((c) => c.classList.add("visible"));
      return;
    }

    // Staggered reveal — feels like watching the scan
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
      el.modulusLens.checked &&
      (pattern === "mixed" || (pred && pred.modulusHint));

    el.modulusControls.hidden = !show;
    if (!show) {
      modulusMode = null;
      return;
    }

    const mods = [3, 4, 5, 8];
    const preferred = pred && pred.modulusHint ? pred.modulusHint : 4;
    if (modulusMode == null) modulusMode = preferred;

    el.modBtns.innerHTML = "";
    const off = document.createElement("button");
    off.type = "button";
    off.textContent = "off";
    off.className = modulusMode == null ? "active" : "";
    off.addEventListener("click", () => {
      modulusMode = null;
      applyModulusColors();
      setupModulusUi(results);
      el.thresholdNote.textContent = el.thresholdNote.textContent; // refresh via paint partial
      paintStripLegendOnly();
    });
    el.modBtns.appendChild(off);

    for (const m of mods) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = String(m);
      b.className = modulusMode === m ? "active" : "";
      b.addEventListener("click", () => {
        modulusMode = m;
        applyModulusColors();
        setupModulusUi(results);
        paintStripLegendOnly();
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
    if (!pyReady || !pyodide) {
      setStatus("Python runtime not ready yet.", "error");
      return;
    }
    if (scanning) return;

    const pred = getSelectedPredicate();
    if (!pred) {
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
    if (el.modulusLens.checked && pred.modulusHint) {
      modulusMode = pred.modulusHint;
    } else if (!el.modulusLens.checked) {
      modulusMode = null;
    }

    scanning = true;
    el.runBtn.disabled = true;
    el.runBtn.textContent = "Scanning…";
    setStatus(`Scanning primes from ${start} to ${limit} (precision ${precision})…`, "busy");
    el.results.hidden = false;

    try {
      // Import modules fresh enough; demo modules already on path
      const py = `
import importlib
import json
from ake_scanner.logic.scanner import scan_primes, results_to_jsonable
from ake_scanner.cli import format_text_report

mod_name = ${JSON.stringify(pred.module)}
fn_name = ${JSON.stringify(pred.function)}
mod = importlib.import_module(mod_name)
fn = getattr(mod, fn_name)
results = scan_primes(
    fn,
    prime_limit=${limit},
    start=${start},
    precision=${precision},
    progress=False,
)
report = format_text_report(results, verbose=${verbose ? "True" : "False"}, full=False)
payload = results_to_jsonable(results)
json.dumps({"report": report, "results": payload})
`;
      const raw = await pyodide.runPythonAsync(py);
      const data = JSON.parse(raw);
      lastResults = data.results;

      buildStory(data.results, pred);
      paintStrip(data.results, { animate: true });

      el.cliReport.textContent = data.report;
      el.jsonReport.textContent = JSON.stringify(data.results, null, 2);
      el.cliCmd.textContent = cliCommand(pred, start, limit, precision, verbose);

      const a = data.results.asymptotic || {};
      setStatus(
        `Done · ${a.pattern || "?"} · pass ${data.results.verified_count} / fail ${data.results.failed_count} / err ${data.results.error_count}`
      );

      el.results.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      console.error(err);
      setStatus(`Scan failed: ${err.message || err}`, "error");
    } finally {
      scanning = false;
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

  function wireForm() {
    el.group.addEventListener("change", fillPredicates);
    el.predicate.addEventListener("change", () => {
      updateClaimCard();
      applyPredicateDefaults(getSelectedPredicate());
    });
    el.limit.addEventListener("input", updateLimitHint);
    el.modulusLens.addEventListener("change", () => {
      if (!el.modulusLens.checked) {
        modulusMode = null;
        if (lastResults) {
          applyModulusColors();
          setupModulusUi(lastResults);
          paintStripLegendOnly();
        }
      } else {
        const p = getSelectedPredicate();
        modulusMode = (p && p.modulusHint) || 4;
        if (lastResults) {
          applyModulusColors();
          setupModulusUi(lastResults);
          paintStripLegendOnly();
        }
      }
    });
    el.form.addEventListener("submit", (e) => {
      e.preventDefault();
      runScan();
    });
  }

  async function maybeSmokeTest() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("smoke") !== "1") return;
    const started = Date.now();
    const waitReady = async () => {
      const deadline = Date.now() + 120000;
      while (!pyReady && Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 200));
      }
      if (!pyReady) throw new Error("Pyodide not ready for smoke test");
    };
    try {
      await waitReady();
      el.predicate.value = "one_plus_t_is_square";
      updateClaimCard();
      applyPredicateDefaults(catalog.byId.one_plus_t_is_square);
      el.limit.value = "30";
      await runScan();
      const pattern = (lastResults && lastResults.asymptotic && lastResults.asymptotic.pattern) || "?";
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
  }

  function boot() {
    fillGroups();
    fillPredicates();
    // Default to the classic eventually_true demo
    if (catalog.byId.one_plus_t_is_square) {
      el.predicate.value = "one_plus_t_is_square";
      updateClaimCard();
      applyPredicateDefaults(catalog.byId.one_plus_t_is_square);
    }
    buildGuided();
    setupTabs();
    setupCopyButtons();
    wireForm();
    initPyodide().then(() => maybeSmokeTest());
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
