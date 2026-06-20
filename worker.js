/**
 * worker.js
 * =========
 * Pyodide Web Worker for the Live LaTeX Calculator.
 *
 * This worker:
 *  1. Boots Pyodide and loads the Python backend (latex_calculator.py).
 *  2. Listens for { id, latexInput, settings? } messages from the main thread.
 *  3. Calls evaluate_latex(latexInput, settingsJson) synchronously inside
 *     Python and posts back { id, status, result?, approx?, error? }.
 *
 * The `id` field lets the main thread discard stale responses when the user
 * types faster than Pyodide can evaluate.
 *
 * The `settings` field is a plain JS object forwarded from the frontend's
 * settings state.  It is JSON-serialised before being handed to Python so
 * that it crosses the JS→Pyodide boundary without requiring pyodide.toPy().
 * Currently recognised Python-side keys:
 *   assumeReal     {boolean}  — treat free variables as real numbers
 *   assumePositive {boolean}  — treat free variables as strictly positive
 *   assumeInteger  {boolean}  — treat free variables as integers
 */

// ── 1. Load Pyodide ─────────────────────────────────────────────────────────
importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.0/full/pyodide.js");

let pyodide = null;
let isReady = false;

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

// Kick off initialisation immediately.
init().catch(err => {
  self.postMessage({ status: "init_error", error: String(err) });
});


// ── 2. Message handler ───────────────────────────────────────────────────────
self.onmessage = async ({ data }) => {
  const { id, blockId, latexInput, settings } = data;

  if (!isReady) {
    self.postMessage({ id, blockId, status: "incomplete", error: "Worker not ready yet." });
    return;
  }

  // Serialise the settings object to JSON so it can cross the JS→Python
  // boundary cleanly without requiring pyodide.toPy() magic.
  // Defaults to '{}' if the main thread sends no settings.
  let settingsJson = "{}";
  try {
    settingsJson = JSON.stringify(settings || {});
  } catch (_) {
    settingsJson = "{}";
  }

  try {
    // evaluate_latex always returns a JSON string and never throws.
    const evaluate = pyodide.globals.get("evaluate_latex");
    const jsonStr  = evaluate(latexInput, settingsJson);
    const response = JSON.parse(jsonStr);
    self.postMessage({ id, blockId, ...response });
  } catch (err) {
    // Safety net — should never be reached because evaluate_latex is defensive.
    self.postMessage({
      id,
      blockId,
      status: "error",
      error: `Worker exception: ${err.message}`,
    });
  }
};
