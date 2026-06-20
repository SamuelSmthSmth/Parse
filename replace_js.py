import sys
import re

with open("index.html", "r") as f:
    content = f.read()

# The JS sections start at SECTION 4
start_marker = "/* ════════════════════════════════════════════════════════════════════════\n   SECTION 4 — "
if start_marker not in content:
    print("Could not find SECTION 4")
    sys.exit(1)

start_idx = content.find(start_marker)
end_idx = content.find("</script>\n</body>")

new_js = """/* ════════════════════════════════════════════════════════════════════════
   SECTION 4 — NOTEBOOK STATE
════════════════════════════════════════════════════════════════════════ */

// Array of blocks: { id, latex, approx }
let blocks = [];
let activeBlockId = null;

function _saveNotebook() {
  // Save only ID, latex, and approx (if any) to avoid saving large DOM/status states
  const data = blocks.map(b => ({
    id: b.id,
    latex: b.latex,
    approx: b.approx || null
  }));
  _lsSave(LS.INPUT, data);
}

/* ════════════════════════════════════════════════════════════════════════
   SECTION 5 — WORKER THREAD POOL & ROUTING
════════════════════════════════════════════════════════════════════════ */

const WORKER_COUNT = 2;
const workers = [];
let readyCount = 0;
let requestSequence = 0;

// Queue for pending requests when all workers are busy
// Maps blockId -> { latex, sequenceId }
const pendingQueue = new Map();

for (let i = 0; i < WORKER_COUNT; i++) {
  const w = new Worker('worker.js?v=4');
  workers.push({ worker: w, idle: true });

  w.onmessage = ({ data }) => {
    if (data.status === 'progress') {
      if (i === 0) { // Only show progress for the first worker
        setWorkerStatus('loading');
        workerLabel.textContent = data.step;
      }
      return;
    }

    if (data.status === 'ready') {
      readyCount++;
      if (readyCount === WORKER_COUNT) {
        setWorkerStatus('ready');
        // Initial boot eval:
        blocks.forEach(b => { if (b.latex.trim()) sendToWorker(b.id, b.latex); });
      }
      return;
    }

    if (data.status === 'init_error') {
      setWorkerStatus('error');
      return;
    }

    workers[i].idle = true;

    // Discard stale responses
    const block = blocks.find(b => b.id === data.blockId);
    if (block && data.id === block.latestSeq) {
      _handleWorkerResponse(block, data);
    }

    _processQueue();
  };

  w.onerror = (e) => {
    console.error(`[worker ${i}] Uncaught error:`, e);
    workers[i].idle = true;
    setWorkerStatus('error');
    _processQueue();
  };
}

function _processQueue() {
  const idleWorker = workers.find(w => w.idle);
  if (!idleWorker) return;
  if (pendingQueue.size === 0) return;

  const [blockId, req] = pendingQueue.entries().next().value;
  pendingQueue.delete(blockId);

  idleWorker.idle = false;
  idleWorker.worker.postMessage({
    id: req.sequenceId,
    blockId: blockId,
    latexInput: req.latex,
    settings: { assumeReal: settings.assumeReal }
  });
}

function sendToWorker(blockId, latex) {
  const block = blocks.find(b => b.id === blockId);
  if (!block) return;

  requestSequence++;
  block.latestSeq = requestSequence;

  if (readyCount < WORKER_COUNT) {
    pendingQueue.set(blockId, { latex, sequenceId: requestSequence });
    return;
  }

  const idleWorker = workers.find(w => w.idle);
  if (idleWorker) {
    idleWorker.idle = false;
    idleWorker.worker.postMessage({
      id: requestSequence,
      blockId: blockId,
      latexInput: latex,
      settings: { assumeReal: settings.assumeReal }
    });
  } else {
    pendingQueue.set(blockId, { latex, sequenceId: requestSequence });
  }
}

function setWorkerStatus(state) {
  workerBadge.setAttribute('data-state', state);
  workerLabel.textContent = state;
}

function _handleWorkerResponse(block, data) {
  if (data.status === 'success') {
    _clearErrorGlow();
    _renderKatex(block.id, data.result);
    if (data.approx) {
      block.approx = data.approx;
      if (settings.showApprox) _renderApprox(block.id, data.approx);
    } else {
      block.approx = null;
      _hideApprox(block.id);
    }
  } else if (data.status === 'incomplete') {
    _scheduleErrorGlow();
    _hideApprox(block.id);
  } else if (data.status === 'error') {
    _clearErrorGlow();
    _showError(block.id, data.error ?? 'Evaluation error');
    _hideApprox(block.id);
  }
}


/* ════════════════════════════════════════════════════════════════════════
   SECTION 6 — SYNTAX ERROR GLOW
════════════════════════════════════════════════════════════════════════ */

let _errGlowTimer = null;
let _errGlowing   = false;

function _scheduleErrorGlow() {
  if (_errGlowing) return;
  clearTimeout(_errGlowTimer);
  _errGlowTimer = setTimeout(_applyErrorGlow, ERR_GLOW_MS);
}

function _applyErrorGlow() {
  _errGlowing = true;
  caret.style.background  = 'var(--caret-err)';
  caret.style.boxShadow   = '0 0 8px var(--caret-err-glow), 0 0 22px var(--caret-err-glow)';
}

function _clearErrorGlow() {
  clearTimeout(_errGlowTimer);
  _errGlowing = false;
  caret.style.background  = '';
  caret.style.boxShadow   = '';
}


/* ════════════════════════════════════════════════════════════════════════
   SECTION 7 — RENDERING
════════════════════════════════════════════════════════════════════════ */

function _renderKatex(blockId, latex) {
  const katexOut = document.getElementById(`out-${blockId}`);
  if (!katexOut) return;
  katex.render(latex, katexOut, {
    displayMode:  true,
    throwOnError: false,
    output:       'html',
    trust:        false,
  });
  _fitOutput(blockId);
}

function _renderApprox(blockId, approxLatex) {
  const approxOut = document.getElementById(`approx-${blockId}`);
  if (!approxOut) return;
  try {
    katex.render('\\\\approx ' + approxLatex, approxOut, {
      displayMode:  false,
      throwOnError: false,
      output:       'html',
      trust:        false,
    });
    approxOut.classList.add('visible');
  } catch(_) {
    approxOut.classList.remove('visible');
  }
}

function _hideApprox(blockId) {
  const approxOut = document.getElementById(`approx-${blockId}`);
  if (approxOut) approxOut.classList.remove('visible');
}

function _showHint(blockId) {
  const katexOut = document.getElementById(`out-${blockId}`);
  const outputScale = document.getElementById(`scale-out-${blockId}`);
  if (!katexOut || !outputScale) return;
  katexOut.innerHTML = '<span class="output-hint">result appears here</span>';
  outputScale.style.transform = '';
  _hideApprox(blockId);
}

function _showError(blockId, msg) {
  const katexOut = document.getElementById(`out-${blockId}`);
  const outputScale = document.getElementById(`scale-out-${blockId}`);
  if (!katexOut || !outputScale) return;
  katexOut.innerHTML = `<span style="font-family:var(--mono);font-size:0.82em;color:var(--err);">${_esc(msg)}</span>`;
  outputScale.style.transform = '';
}

function _esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}


/* ════════════════════════════════════════════════════════════════════════
   SECTION 8 — BLOCK MANAGEMENT (NOTEBOOK DOM)
════════════════════════════════════════════════════════════════════════ */

function _generateId() {
  return Math.random().toString(36).substring(2, 9);
}

function _createBlock(initialLatex = '', approx = null, focusAfter = false) {
  const blockId = _generateId();
  const block = { id: blockId, latex: initialLatex, approx: approx, latestSeq: 0 };
  blocks.push(block);

  const container = document.getElementById('blocks-container');
  const el = document.createElement('div');
  el.className = 'block';
  el.id = `block-${blockId}`;
  
  el.innerHTML = `
    <section class="pane pane-input" aria-label="LaTeX input">
      <div class="scale-wrapper" id="scale-in-${blockId}">
        <textarea
          id="in-${blockId}"
          class="latex-input"
          rows="1"
          wrap="off"
          spellcheck="false"
          autocorrect="off"
          autocomplete="off"
          autocapitalize="off"
          aria-label="Type a LaTeX expression"
          placeholder="\\\\int_{0}^{1} x^2 \\\\, dx"
        ></textarea>
      </div>
    </section>
    <section class="pane pane-output" aria-label="Rendered result">
      <div class="scale-wrapper" id="scale-out-${blockId}">
        <div id="out-${blockId}" class="katex-output" role="math" aria-live="polite">
          <span class="output-hint">result appears here</span>
        </div>
      </div>
      <div id="approx-${blockId}" class="approx-output" aria-live="polite"></div>
    </section>
  `;
  container.appendChild(el);

  const ta = document.getElementById(`in-${blockId}`);
  ta.value = initialLatex;

  _bindBlockEvents(blockId, ta);
  
  // Observe for resizing
  _ro.observe(el.querySelector('.pane-input'));
  _ro.observe(el.querySelector('.pane-output'));

  _resizeHeight(ta);
  _fitInput(blockId);
  
  if (focusAfter) {
    ta.focus();
    // Scroll smoothly to the new block
    ta.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  return blockId;
}

let _debounceMap = new Map();

function _bindBlockEvents(blockId, ta) {
  ta.addEventListener('input', () => {
    _clearErrorGlow();
    _resizeHeight(ta);
    _fitInput(blockId);
    _updateCaret();

    const block = blocks.find(b => b.id === blockId);
    if (block) block.latex = ta.value;
    _saveNotebook();

    if (!ta.value.trim()) {
      _showHint(blockId);
      clearTimeout(_debounceMap.get(blockId));
      return;
    }

    clearTimeout(_debounceMap.get(blockId));
    _debounceMap.set(blockId, setTimeout(() => sendToWorker(blockId, ta.value), DEBOUNCE_MS));
  });

  ['keyup', 'keydown', 'click', 'select'].forEach(evt =>
    ta.addEventListener(evt, (e) => {
      // Shift+Enter mechanic
      if (evt === 'keydown' && e.key === 'Enter' && e.shiftKey) {
        e.preventDefault();
        ta.blur();
        _createBlock('', null, true);
        return;
      }
      _updateCaret();
    })
  );

  ta.addEventListener('focus', () => {
    activeBlockId = blockId;
    caret.style.opacity = '1';
    _updateCaret();
  });

  ta.addEventListener('blur', () => {
    if (activeBlockId === blockId) {
      activeBlockId = null;
      caret.style.opacity = '0';
    }
  });
}

function _resizeHeight(ta) {
  ta.style.height = 'auto';
  ta.style.height = ta.scrollHeight + 'px';
}


/* ════════════════════════════════════════════════════════════════════════
   SECTION 9 — SHRINK-TO-FIT
════════════════════════════════════════════════════════════════════════ */

function _fitInput(blockId) {
  const ta = document.getElementById(`in-${blockId}`);
  const scaleWrapper = document.getElementById(`scale-in-${blockId}`);
  const pane = scaleWrapper?.parentElement;
  if (!ta || !scaleWrapper || !pane) return;

  _syncMirror(ta);
  mirror.style.width = 'auto';
  mirror.innerHTML   = _mirrorEsc(ta.value) || '\\u00a0';

  const minW     = window.innerWidth * MIN_W_VW;
  const contentW = Math.max(minW, mirror.scrollWidth);

  ta.style.width = contentW + 'px';

  const available = pane.clientWidth * SAFE_MARGIN;
  const scale     = contentW > available ? available / contentW : 1;
  scaleWrapper.style.transform = scale < 1 ? `scale(${scale.toFixed(5)})` : '';
}

function _fitOutput(blockId) {
  const katexOut = document.getElementById(`out-${blockId}`);
  const scaleWrapper = document.getElementById(`scale-out-${blockId}`);
  const pane = scaleWrapper?.parentElement;
  if (!katexOut || !scaleWrapper || !pane) return;

  const contentW  = katexOut.scrollWidth;
  const available = pane.clientWidth * SAFE_MARGIN;
  const scale     = contentW > available ? available / contentW : 1;
  scaleWrapper.style.transform = scale < 1 ? `scale(${scale.toFixed(5)})` : '';
}

const _ro = new ResizeObserver((entries) => {
  // To avoid recalculating EVERYTHING, we could check the entries, 
  // but let's just refit the blocks that were resized.
  entries.forEach(entry => {
    const pane = entry.target;
    const isInput = pane.classList.contains('pane-input');
    const blockEl = pane.closest('.block');
    if (!blockEl) return;
    const blockId = blockEl.id.replace('block-', '');
    if (isInput) _fitInput(blockId);
    else _fitOutput(blockId);
  });
});


/* ════════════════════════════════════════════════════════════════════════
   SECTION 10 — MIRROR SYNC & CUSTOM CARET
════════════════════════════════════════════════════════════════════════ */

function _syncMirror(ta) {
  const cs = getComputedStyle(ta);
  MIRROR_PROPS.forEach(p => { mirror.style[p] = cs[p]; });
}

function _mirrorEsc(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/ /g, '&nbsp;').replace(/\\n/g, '<br>');
}

function _updateCaret() {
  if (!activeBlockId) {
    caret.style.opacity = '0';
    return;
  }
  
  const ta = document.getElementById(`in-${activeBlockId}`);
  const scaleWrapper = document.getElementById(`scale-in-${activeBlockId}`);
  if (!ta || document.activeElement !== ta) {
    caret.style.opacity = '0';
    return;
  }

  _syncMirror(ta);

  const sel   = ta.selectionStart ?? 0;
  const pre   = _mirrorEsc(ta.value.slice(0, sel));
  const post  = _mirrorEsc(ta.value.slice(sel));

  mirror.style.width = ta.offsetWidth + 'px';
  mirror.innerHTML   = pre + '<span id="csent">\\u200b</span>' + post;

  const sentinel = document.getElementById('csent');
  if (!sentinel) { caret.style.opacity = '0'; return; }

  const sRect = sentinel.getBoundingClientRect();
  const mRect = mirror.getBoundingClientRect();
  const tRect = ta.getBoundingClientRect();

  const natX = sRect.left - mRect.left;
  const natY = sRect.top  - mRect.top;

  const matrix = new DOMMatrix(getComputedStyle(scaleWrapper).transform);
  const scale  = matrix.a || 1;

  const fs     = parseFloat(getComputedStyle(ta).fontSize) * scale;
  const lineH  = sRect.height * scale;
  const caretH = fs * 1.20;

  const cx = tRect.left + natX * scale;
  const cy = tRect.top  + natY * scale + (lineH - caretH) / 2;

  caret.style.left    = cx + 'px';
  caret.style.top     = cy + 'px';
  caret.style.height  = caretH + 'px';
  caret.style.opacity = '1';
}

document.addEventListener('selectionchange', _updateCaret);
window.addEventListener('scroll', _updateCaret, { passive: true });
document.getElementById('app').addEventListener('scroll', _updateCaret, { passive: true });


/* ════════════════════════════════════════════════════════════════════════
   SECTION 11 — INIT (LOCALSTORAGE HYDRATION)
════════════════════════════════════════════════════════════════════════ */

(function init() {
  const savedTheme = _lsLoad(LS.THEME, true);
  _applyTheme(savedTheme);

  settings.showApprox = _lsLoad(LS.SHOW_APPROX, false);
  settings.assumeReal = _lsLoad(LS.ASSUME_REAL, false);
  _syncApproxToggle();
  _syncAssumptionToggle();

  // Load Notebook array
  let savedNotebook = _lsLoad(LS.INPUT, null);
  
  if (Array.isArray(savedNotebook) && savedNotebook.length > 0) {
    savedNotebook.forEach(b => {
      _createBlock(b.latex || '', b.approx || null, false);
    });
  } else if (typeof savedNotebook === 'string' && savedNotebook.length > 0) {
    // Migration path from single-string MVP
    _createBlock(savedNotebook, null, false);
  } else {
    // Brand new session
    _createBlock('', null, false);
  }

  setWorkerStatus('loading');
  
  // Focus the last block by default
  const lastId = blocks[blocks.length - 1].id;
  const lastTa = document.getElementById(`in-${lastId}`);
  if (lastTa) lastTa.focus();
})();
"""

new_content = content[:start_idx] + new_js + "\n</script>\n</body>\n</html>\n"
with open("index.html", "w") as f:
    f.write(new_content)
