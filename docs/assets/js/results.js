/** Story panel + final prime strip rendering. */

import {
  applyModulusColors,
  paintStripLegendOnly,
  renderModulusAnalysis,
  setupModulusUi,
} from "./modulus.js";
import { el, state } from "./state.js";
import { escapeHtml } from "./util.js";

export function statusForPrime(results, p) {
  if (results.passed_primes.includes(p)) return "pass";
  if (results.failed_primes.includes(p)) return "fail";
  if (results.error_primes.includes(p)) return "error";
  return "pending";
}

function formatWitness(wit) {
  if (!wit) return "";
  if (wit.kind === "laurent") {
    if (wit.zero) return "witness: 0";
    const parts = [];
    const entries = Object.entries(wit.coeffs || {}).sort(
      (a, b) => Number(a[0]) - Number(b[0])
    );
    for (const [d, c] of entries.slice(0, 10)) {
      const deg = Number(d);
      if (deg === 0) parts.push(String(c));
      else if (deg === 1) parts.push(`${c}·t`);
      else parts.push(`${c}·t^${deg}`);
    }
    if (wit.truncated || entries.length > 10) parts.push("…");
    return `witness series (mod ${wit.prime}, prec ${wit.precision}):\n  ` + parts.join(" + ");
  }
  if (wit.kind === "residue") {
    return `residue witness: root ${wit.root} with value ≡ ${wit.value} (mod ${wit.prime})`;
  }
  return JSON.stringify(wit, null, 2);
}

export function showExplanation(p) {
  const panel = el.explainPanel;
  if (!panel) return;
  const results = state.lastResults;
  if (!results) {
    panel.hidden = true;
    return;
  }
  const st = statusForPrime(results, p);
  const explMap = results.explanations || {};
  const entry = explMap[p] || explMap[String(p)];

  el.explainTitle.textContent = `p = ${p} · ${st}`;
  el.primeStrip.querySelectorAll(".prime-cell.selected").forEach((c) => {
    c.classList.remove("selected");
  });
  const cell = el.primeStrip.querySelector(`.prime-cell[data-prime="${p}"]`);
  if (cell) cell.classList.add("selected");

  if (!entry) {
    el.explainBody.textContent =
      "No structured explanation for this prime (predicate returned a bare bool, or explanations were not recorded).";
    el.explainWitness.hidden = true;
    panel.hidden = false;
    return;
  }

  const code = entry.code || "?";
  const msg = entry.message || "";
  el.explainBody.innerHTML = `<strong class="mono">${escapeHtml(code)}</strong> — ${escapeHtml(msg)}`;

  const witText = formatWitness(entry.witness);
  if (witText) {
    el.explainWitness.textContent = witText;
    el.explainWitness.hidden = false;
  } else {
    el.explainWitness.hidden = true;
  }
  panel.hidden = false;
}

export function buildStory(results, pred) {
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
    eventually_true: `After finitely many exceptions, φ holds on a long clean tail of larger primes. That is the AKE-shaped signal this tool is built to surface: empirical evidence that the sentence is true for all sufficiently large p (within the scanned window). Raise the limit to stress-test the threshold N.`,
    eventually_false: `After a finite early stretch, φ fails for every larger prime in range. Read this as asymptotic failure in the sample — dual to eventually_true — not a single unlucky prime.`,
    always_true: `φ held for every prime scanned. Constant truth on this window: no exceptional set and no threshold drama (often a simple constructive witness).`,
    always_false: `φ failed for every prime scanned. Often a structural obstruction (odd valuation, characteristic, non-surjectivity) rather than “needs larger p.”`,
    mixed: `No single threshold N. Truth oscillates with p — typically a congruence condition (quadratic residue, roots of unity, …). Use the residue-class analysis below; raising the limit alone will not produce eventually_true.`,
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

export function paintStrip(results, { animate = true } = {}) {
  const primes = results.primes_scanned || [];
  const a = results.asymptotic || {};
  const threshold = a.threshold;
  const tailSet = new Set(a.tail_primes || []);
  const token = ++state.stripAnimToken;

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
    cell.title = `p=${p} · ${st} — click for explanation`;
    cell.setAttribute("aria-label", `Prime ${p}, ${st}. Click for explanation.`);
    if (threshold != null && p === threshold) cell.classList.add("threshold-mark");
    if (tailSet.has(p)) cell.classList.add("tail");
    cell.addEventListener("click", () => showExplanation(p));
    el.primeStrip.appendChild(cell);
    cells.push(cell);
  }

  // Hide previous selection until user clicks
  if (el.explainPanel) el.explainPanel.hidden = true;

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
    (state.modulusMode
      ? `Residue lens: color = p mod ${state.modulusMode}; inset ring still shows pass/fail.`
      : "");

  setupModulusUi(results);

  if (!animate || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    cells.forEach((c) => c.classList.add("visible"));
    return;
  }

  let i = 0;
  const batch = Math.max(1, Math.ceil(cells.length / 40));
  function step() {
    if (token !== state.stripAnimToken) return;
    const end = Math.min(i + batch, cells.length);
    for (; i < end; i++) cells[i].classList.add("visible");
    if (i < cells.length) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

export function cliCommand(pred, start, limit, precision, verbose) {
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

export function setupTabs() {
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

export function setupCopyButtons() {
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
