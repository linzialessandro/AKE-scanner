/** Download helpers for scan results. */

import { el, setStatus, state } from "./state.js";

export function resultsToCsv(results) {
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

export function downloadBlob(filename, text, mime) {
  const blob = new Blob([text], { type: mime || "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function exportBasename() {
  const id = (state.lastPredicate && state.lastPredicate.id) || "scan";
  const lim = (state.lastResults && state.lastResults.prime_limit) || el.limit.value || "";
  return `ake-${id}-l${lim}`;
}

export function setupExport() {
  el.exportTxt.addEventListener("click", () => {
    if (!state.lastReport) {
      setStatus("Nothing to export yet — run a scan first.", "error");
      return;
    }
    downloadBlob(`${exportBasename()}.txt`, state.lastReport, "text/plain");
  });
  el.exportJson.addEventListener("click", () => {
    if (!state.lastResults) {
      setStatus("Nothing to export yet — run a scan first.", "error");
      return;
    }
    downloadBlob(
      `${exportBasename()}.json`,
      JSON.stringify(state.lastResults, null, 2),
      "application/json"
    );
  });
  el.exportCsv.addEventListener("click", () => {
    if (!state.lastResults) {
      setStatus("Nothing to export yet — run a scan first.", "error");
      return;
    }
    downloadBlob(`${exportBasename()}.csv`, resultsToCsv(state.lastResults), "text/csv");
  });
}
