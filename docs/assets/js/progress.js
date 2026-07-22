/** Progress bar + live prime-strip updates during a scan. */

import { el, setStatus, state } from "./state.js";

export function setProgress(done, total, p, status) {
  if (!el.progressBlock) return;
  el.progressBlock.hidden = false;
  const pct = total ? Math.round((100 * done) / total) : 0;
  el.progressFill.style.width = `${pct}%`;
  el.progressLabel.textContent =
    done < total ? `Scanning p = ${p} (${status})…` : "Finishing report…";
  el.progressCounts.textContent = `${done} / ${total}`;
}

export function hideProgress() {
  if (!el.progressBlock) return;
  el.progressBlock.hidden = true;
  el.progressFill.style.width = "0%";
}

export function beginLiveStrip() {
  state.stripAnimToken += 1;
  el.primeStrip.innerHTML = "";
  state.liveStrip = { cells: new Map() };
  el.results.hidden = false;
  el.modulusAnalysis.hidden = true;
  el.thresholdNote.textContent = "Live scan — cells appear as each prime finishes.";
}

export function appendLiveCell(p, status) {
  if (!state.liveStrip) return;
  if (state.liveStrip.cells.has(p)) return;
  const cell = document.createElement("button");
  cell.type = "button";
  cell.className = `prime-cell ${status} visible`;
  cell.setAttribute("role", "listitem");
  cell.dataset.prime = String(p);
  cell.dataset.status = status;
  cell.textContent = String(p);
  cell.title = `p=${p} · ${status}`;
  cell.setAttribute("aria-label", `Prime ${p}, ${status}`);
  // Full click handler re-bound after final paintStrip; interim no-op is fine
  el.primeStrip.appendChild(cell);
  state.liveStrip.cells.set(p, cell);
}

export function handleProgress(msg) {
  const { done, total, p, status } = msg;
  setProgress(done, total, p, status);
  appendLiveCell(p, status);
  setStatus(`Scanning… ${done}/${total} (p=${p})`, "busy");
}
