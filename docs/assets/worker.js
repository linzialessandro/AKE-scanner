/**
 * Pyodide worker for AKE Scanner — keeps the UI thread responsive.
 *
 * Messages (main → worker):
 *   { type: "init", baseUrl, pyodideCdn, pyFiles }
 *   { type: "scan", requestId, mode: "catalog"|"custom", ... }
 *
 * Messages (worker → main):
 *   { type: "ready", version }
 *   { type: "progress", requestId, done, total, p, status }
 *   { type: "result", requestId, results, report }
 *   { type: "error", requestId?, message }
 *   { type: "log", message }
 */
/* eslint-disable no-restricted-globals */

const DEFAULT_PY_FILES = [
  "ake_scanner/__init__.py",
  "ake_scanner/__main__.py",
  "ake_scanner/cli.py",
  "ake_scanner/predicates.py",
  "ake_scanner/reporting.py",
  "ake_scanner/algebra/__init__.py",
  "ake_scanner/algebra/laurent.py",
  "ake_scanner/algebra/hensel.py",
  "ake_scanner/logic/__init__.py",
  "ake_scanner/logic/primes.py",
  "ake_scanner/logic/asymptotic.py",
  "ake_scanner/logic/scanner.py",
  "examples/demo_hensel.py",
  "examples/advanced_sentences.py",
];

let pyodide = null;
let ready = false;
let initPromise = null;

function post(msg) {
  self.postMessage(msg);
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

async function loadVendor(baseUrl, pyFiles) {
  const root = baseUrl.endsWith("/") ? baseUrl : baseUrl + "/";
  for (const rel of pyFiles) {
    const url = root + "py/" + rel;
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`Failed to fetch py/${rel} (${res.status})`);
    }
    const text = await res.text();
    const fsPath = "/ake_pkg/" + rel;
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

async function initPyodide(baseUrl, pyodideCdn, pyFiles) {
  if (ready && pyodide) return;
  if (initPromise) return initPromise;

  initPromise = (async () => {
    const cdn = pyodideCdn.endsWith("/") ? pyodideCdn : pyodideCdn + "/";
    post({ type: "log", message: "importScripts pyodide.js…" });
    importScripts(cdn + "pyodide.js");
    post({ type: "log", message: "loadPyodide…" });
    // eslint-disable-next-line no-undef
    pyodide = await loadPyodide({ indexURL: cdn });
    post({ type: "log", message: "loading ake_scanner vendor…" });
    await loadVendor(baseUrl, pyFiles || DEFAULT_PY_FILES);
    pyodide.runPython(`
from ake_scanner import __version__
from ake_scanner.logic.scanner import scan_primes, results_to_jsonable
from ake_scanner.reporting import format_text_report
`);
    const version = pyodide.runPython(
      "from ake_scanner import __version__; __version__"
    );
    ready = true;
    post({ type: "ready", version: String(version) });
    post({ type: "log", message: "ready " + version });
  })();

  try {
    await initPromise;
  } catch (err) {
    initPromise = null;
    ready = false;
    post({ type: "log", message: "init failed: " + String(err) });
    throw err;
  }
}

function installProgressBridge(requestId) {
  const cb = (done, total, p, status) => {
    post({
      type: "progress",
      requestId,
      done: Number(done),
      total: Number(total),
      p: Number(p),
      status: String(status),
    });
  };
  pyodide.globals.set("_ake_progress", cb);
}

async function runScan(msg) {
  const {
    requestId,
    mode,
    module,
    functionName,
    customCode,
    start,
    limit,
    precision,
    verbose,
  } = msg;

  if (!ready || !pyodide) {
    throw new Error("Worker not initialized");
  }

  installProgressBridge(requestId);

  if (mode === "custom") {
    pyodide.FS.writeFile(
      "/ake_pkg/examples/_user_predicate.py",
      customCode || ""
    );
  }

  const py = `
import importlib
import json
import sys
from ake_scanner.logic.scanner import scan_primes, results_to_jsonable
from ake_scanner.reporting import format_text_report

def _on_progress(done, total, p, status):
    _ake_progress(done, total, p, status)

mode = ${JSON.stringify(mode)}
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
    mod = importlib.import_module(${JSON.stringify(module || "")})
    fn = getattr(mod, ${JSON.stringify(functionName || "")})

results = scan_primes(
    fn,
    prime_limit=${Number(limit) || 50},
    start=${Number(start) || 2},
    precision=${Number(precision) || 20},
    progress=False,
    on_progress=_on_progress,
)
report = format_text_report(results, verbose=${verbose ? "True" : "False"}, full=False)
payload = results_to_jsonable(results)
json.dumps({"report": report, "results": payload})
`;

  const raw = await pyodide.runPythonAsync(py);
  const data = JSON.parse(raw);
  post({
    type: "result",
    requestId,
    results: data.results,
    report: data.report,
  });
}

self.onmessage = async (ev) => {
  const msg = ev.data || {};
  try {
    if (msg.type === "init") {
      await initPyodide(msg.baseUrl, msg.pyodideCdn, msg.pyFiles);
      return;
    }
    if (msg.type === "scan") {
      await runScan(msg);
      return;
    }
    post({ type: "error", message: `Unknown message type: ${msg.type}` });
  } catch (err) {
    console.error(err);
    post({
      type: "error",
      requestId: msg.requestId,
      message: String((err && err.message) || err),
    });
  }
};
