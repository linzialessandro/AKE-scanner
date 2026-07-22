/** Shareable query-string state. */

import { HARD_LIMIT_CAP } from "./config.js";
import { el, getCatalog, setStatus, state } from "./state.js";
import { b64urlDecode, b64urlEncode } from "./util.js";

export function readQueryState() {
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
    code: params.get("code"),
  };
}

export function applyQueryState(q, { fillPredicates, updateClaimCard, applyPredicateDefaults, updateLimitHint }) {
  const catalog = getCatalog();
  if (q.group && [...el.group.options].some((o) => o.value === q.group)) {
    el.group.value = q.group;
    fillPredicates();
  }
  if (q.p && catalog.byId[q.p]) {
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
  if (q.limit) {
    el.limit.value = String(
      Math.min(HARD_LIMIT_CAP, Math.max(2, parseInt(q.limit, 10) || 50))
    );
  }
  if (q.precision) {
    el.precision.value = String(
      Math.min(80, Math.max(4, parseInt(q.precision, 10) || 20))
    );
  }
  el.verbose.checked = !!q.verbose;
  if (q.lens || q.mod) el.modulusLens.checked = true;
  if (q.mod) {
    const m = parseInt(q.mod, 10);
    if (m > 1) state.modulusMode = m;
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
      /* ignore */
    }
  }
  updateClaimCard();
  updateLimitHint();
}

export function buildShareParams({ includeCode = false } = {}) {
  const params = new URLSearchParams();
  if (el.useCustom.checked) {
    params.set("custom", "1");
    if (includeCode && el.customCode.value.trim()) {
      const encoded = b64urlEncode(el.customCode.value);
      if (encoded.length < 1800) params.set("code", encoded);
    }
  } else {
    const pred = getCatalog().byId[el.predicate.value];
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
  if (state.modulusMode != null) params.set("mod", String(state.modulusMode));
  params.set("autorun", "1");
  return params;
}

export function updateShareUrl() {
  if (!el.shareUrl) return;
  const params = buildShareParams({ includeCode: el.useCustom.checked });
  const url = new URL(window.location.href);
  url.search = params.toString();
  el.shareUrl.textContent = url.toString();
}

export async function copyShareLink() {
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
