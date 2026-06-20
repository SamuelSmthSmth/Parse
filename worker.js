/**
 * worker.js
 * =========
 * Pyodide Web Worker for the Live LaTeX Calculator.
 *
 * This worker:
 *  1. Boots Pyodide and loads the Python backend (latex_calculator.py).
 *  2. Listens for { id, latexInput } messages from the main thread.
 *  3. Calls evaluate_latex() synchronously inside Python and posts back
 *     { id, status, result? | error? } to the main thread.
 *
 * The `id` field lets the main thread discard stale responses when the
 * user types faster than Pyodide can evaluate.
 */

// ── 1. Load Pyodide ─────────────────────────────────────────────────────────
importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.0/full/pyodide.js");

let pyodide   = null;
let isReady   = false;

async function init() {
  self.postMessage({ status: "progress", step: "Loading Pyodide engine..." });
  pyodide = await loadPyodide();

  self.postMessage({ status: "progress", step: "Loading SymPy..." });
  await pyodide.loadPackage(["sympy", "micropip"]);

  self.postMessage({ status: "progress", step: "Fetching ANTLR4..." });
  const micropip = pyodide.pyimport("micropip");
  await micropip.install("antlr4-python3-runtime==4.11");

  self.postMessage({ status: "progress", step: "Loading python backend..." });
  const src = await fetch("latex_calculator.py").then(r => {
    if (!r.ok) throw new Error(`Failed to load latex_calculator.py: ${r.status}`);
    return r.text();
  });
  await pyodide.runPythonAsync(src);

  isReady = true;
  self.postMessage({ status: "ready" });
}

// Kick off initialisation immediately — the main thread should wait for
// the first { status: "ready" } message before sending any requests.
init().catch(err => {
  self.postMessage({ status: "init_error", error: String(err) });
});


// ── 2. Message handler ───────────────────────────────────────────────────────
self.onmessage = async ({ data }) => {
  const { id, latexInput } = data;

  if (!isReady) {
    self.postMessage({ id, status: "incomplete", error: "Worker not ready yet." });
    return;
  }

  try {
    // Call the Python function — it always returns a JSON string, never throws.
    const jsonStr  = pyodide.globals.get("evaluate_latex")(latexInput);
    const response = JSON.parse(jsonStr);
    self.postMessage({ id, ...response });
  } catch (err) {
    // Safety net: should never be reached because evaluate_latex catches everything.
    self.postMessage({ id, status: "error", error: `Worker exception: ${err.message}` });
  }
};
