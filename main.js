/**
 * main.js
 * =======
 * Main-thread integration for the Live LaTeX Calculator.
 *
 * Drop this into your page alongside worker.js and latex_calculator.py.
 * Wire `calculate(latexStr)` to your input's keyup/change event and
 * implement the three callback stubs at the bottom.
 */

// ── Spawn the worker ─────────────────────────────────────────────────────────
const worker = new Worker("worker.js");

// Monotonically increasing counter.  Every new calculate() call increments
// this; stale replies (with a lower id) are silently discarded.
let latestId = 0;
let workerReady = false;

// ── Handle all incoming messages ─────────────────────────────────────────────
worker.onmessage = ({ data }) => {
  // Boot signal — worker finished loading Pyodide + SymPy.
  if (data.status === "ready") {
    workerReady = true;
    onWorkerReady();          // ← implement / remove as needed
    return;
  }

  if (data.status === "init_error") {
    onInitError(data.error);
    return;
  }

  // Discard responses that belong to a previous keystroke.
  if (data.id !== latestId) return;

  if (data.status === "success") {
    onSuccess(data.result);   // data.result is a LaTeX string
  } else if (data.status === "incomplete") {
    onIncomplete(data.error); // transient — user is still typing
  } else {
    onError(data.error);      // hard error (e.g. integral has no closed form)
  }
};

worker.onerror = (e) => {
  console.error("[worker] Uncaught error:", e);
};


// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Send a LaTeX string to the Pyodide worker for evaluation.
 * Safe to call on every keyup — stale responses are automatically discarded.
 *
 * @param {string} latexStr - Raw LaTeX math, e.g. "\\int_{0}^{1} x^2 \\, dx"
 */
export function calculate(latexStr) {
  if (!workerReady) return;   // drop the message; worker still booting
  const id = ++latestId;
  worker.postMessage({ id, latexInput: latexStr });
}


// ── Callbacks (implement these in your UI layer) ──────────────────────────────

function onWorkerReady() {
  // Called once, when Pyodide + SymPy finish loading.
  // e.g. hide a loading spinner, enable the input field.
  console.log("[calculator] Worker ready.");
}

function onSuccess(latexResult) {
  // latexResult is a SymPy-rendered LaTeX string.
  // Pass it to KaTeX / MathJax to render in the DOM.
  // e.g. katex.render(latexResult, document.getElementById("output"));
  console.log("[calculator] Result:", latexResult);
}

function onIncomplete(_errorMsg) {
  // User is still typing — show a subtle "…" or neutral placeholder.
  // Do NOT show an error banner here.
  console.debug("[calculator] Incomplete input, waiting…");
}

function onError(errorMsg) {
  // Hard error: unsupported integral, type error, etc.
  // Show a dismissible error banner.
  console.warn("[calculator] Error:", errorMsg);
}

function onInitError(errorMsg) {
  console.error("[calculator] Worker failed to initialise:", errorMsg);
}
