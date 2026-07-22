/** Pyodide Web Worker + main-thread fallback. */

import {
  PY_FILES,
  PYODIDE_CDN,
  WORKER_INIT_TIMEOUT_MS,
} from "./config.js";
import { handleProgress } from "./progress.js";
import { el, setStatus, state } from "./state.js";
import { assetUrl, loadScript, pageBaseUrl } from "./util.js";

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
from ake_scanner.reporting import format_text_report
`);
}

async function initMainThread() {
  setStatus("Loading Python on main thread (fallback)…", "busy");
  el.runBtn.disabled = true;
  el.runBtn.textContent = "Loading Python…";
  await loadScript(PYODIDE_CDN + "pyodide.js");
  // eslint-disable-next-line no-undef
  state.pyodideMain = await loadPyodide({ indexURL: PYODIDE_CDN });
  await loadVendorIntoMain(state.pyodideMain);
  state.packageVersion = String(
    state.pyodideMain.runPython("from ake_scanner import __version__; __version__")
  );
  state.runtimeMode = "main";
  state.pyReady = true;
  el.runBtn.disabled = false;
  el.runBtn.textContent = "Run scan";
  setStatus(`Ready · ake-scanner ${state.packageVersion} · main thread`);
  return true;
}

function onWorkerMessage(ev) {
  const msg = ev.data || {};
  if (msg.type === "log") {
    console.log("[ake-worker]", msg.message);
    return;
  }
  if (msg.type === "progress" && msg.requestId === state.scanRequestId) {
    handleProgress(msg);
    return;
  }
  if (msg.type === "result" && msg.requestId === state.scanRequestId) {
    if (state.scanResolve) {
      const r = state.scanResolve;
      state.scanResolve = null;
      state.scanReject = null;
      r({ results: msg.results, report: msg.report });
    }
    return;
  }
  if (msg.type === "error" && msg.requestId === state.scanRequestId) {
    if (state.scanReject) {
      const r = state.scanReject;
      state.scanResolve = null;
      state.scanReject = null;
      r(new Error(msg.message || "Scan failed"));
    }
  }
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

      state.worker = new Worker(assetUrl("assets/worker.js"));
      const onReady = (ev) => {
        const msg = ev.data || {};
        if (msg.type === "log") {
          console.log("[ake-worker]", msg.message);
          return;
        }
        if (msg.type === "ready") {
          state.packageVersion = msg.version || "";
          state.runtimeMode = "worker";
          state.pyReady = true;
          el.runBtn.disabled = false;
          el.runBtn.textContent = "Run scan";
          setStatus(`Ready · ake-scanner ${state.packageVersion} · worker`);
          state.worker.removeEventListener("message", onReady);
          finish(true);
        } else if (msg.type === "error" && !state.pyReady) {
          state.worker.removeEventListener("message", onReady);
          finish(false, new Error(msg.message || "Worker init failed"));
        }
      };
      state.worker.addEventListener("message", onReady);
      state.worker.addEventListener("message", onWorkerMessage);
      state.worker.onerror = (err) => {
        console.error(err);
        finish(false, new Error(err.message || "Worker error"));
      };
      state.worker.postMessage({
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

export async function initRuntime() {
  try {
    const w = await tryInitWorker(WORKER_INIT_TIMEOUT_MS);
    if (w.ok) return true;
    console.warn("Worker unavailable, falling back to main thread:", w.err);
    if (state.worker) {
      try {
        state.worker.terminate();
      } catch (_) {
        /* ignore */
      }
      state.worker = null;
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

function workerScan(payload) {
  return new Promise((resolve, reject) => {
    if (!state.worker || !state.pyReady) {
      reject(new Error("Worker not ready"));
      return;
    }
    state.scanRequestId += 1;
    const requestId = state.scanRequestId;
    state.scanResolve = resolve;
    state.scanReject = reject;
    state.worker.postMessage({ type: "scan", requestId, ...payload });
  });
}

async function mainThreadScan(payload) {
  const py = state.pyodideMain;
  if (!py) throw new Error("Main-thread Pyodide not ready");

  state.scanRequestId += 1;
  const requestId = state.scanRequestId;
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
from ake_scanner.reporting import format_text_report

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

export async function runEngineScan(payload) {
  if (state.runtimeMode === "worker") return workerScan(payload);
  if (state.runtimeMode === "main") return mainThreadScan(payload);
  throw new Error("Runtime not ready");
}
