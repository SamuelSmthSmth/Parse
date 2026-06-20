import sys

with open("index.html", "r") as f:
    content = f.read()

css_inject = """    .steps-container.open {
      max-height: 1000px;
      opacity: 1;
      margin-top: 1rem;
    }
    .step-item {
      font-size: 0.95em;
      color: var(--fg-dim);
    }
    
    @keyframes pulse-thinking {
      0% { opacity: 0.4; }
      50% { opacity: 0.7; }
      100% { opacity: 0.4; }
    }
    .pane-output.thinking {
      opacity: 0.5;
      animation: pulse-thinking 1.5s infinite ease-in-out;
      pointer-events: none;
    }"""

content = content.replace("""    .steps-container.open {
      max-height: 1000px;
      opacity: 1;
      margin-top: 1rem;
    }
    .step-item {
      font-size: 0.95em;
      color: var(--fg-dim);
    }""", css_inject)


worker_pool_old = """const WORKER_COUNT = 2;
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
      settings: { assumeReal: settings.assumeReal, useDegrees: settings.useDegrees, precision: settings.precision, stepsMode: settings.stepsMode }
    });
  } else {
    pendingQueue.set(blockId, { latex, sequenceId: requestSequence });
  }
}"""

worker_pool_new = """const WORKER_COUNT = 2;
const workers = [];
let readyCount = 0;
let requestSequence = 0;

// Queue for pending requests when all workers are busy
// Maps blockId -> { latex, sequenceId }
const pendingQueue = new Map();

function _createWorker(i) {
  const w = new Worker('worker.js?v=4');
  if (!workers[i]) workers[i] = { worker: null, idle: true };
  workers[i].worker = w;
  workers[i].idle = true;

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

    const block = blocks.find(b => b.id === data.blockId);
    if (block) {
      if (block.watchdogTimer) {
        clearTimeout(block.watchdogTimer);
        block.watchdogTimer = null;
      }
      _clearThinkingState(block.id);
      
      // Discard stale responses
      if (data.id === block.latestSeq) {
        _handleWorkerResponse(block, data);
      }
    }

    _processQueue();
  };

  w.onerror = (e) => {
    console.error(`[worker ${i}] Uncaught error:`, e);
    workers[i].idle = true;
    setWorkerStatus('error');
    
    // Clear any block associated with this worker
    blocks.forEach(block => {
      if (block.activeWorkerIndex === i) {
        if (block.watchdogTimer) {
          clearTimeout(block.watchdogTimer);
          block.watchdogTimer = null;
        }
        _clearThinkingState(block.id);
      }
    });
    
    _processQueue();
  };
}

for (let i = 0; i < WORKER_COUNT; i++) {
  _createWorker(i);
}

function _setThinkingState(blockId) {
  const el = document.getElementById(`block-${blockId}`);
  if (el) {
    const out = el.querySelector('.pane-output');
    if (out) out.classList.add('thinking');
  }
}

function _clearThinkingState(blockId) {
  const el = document.getElementById(`block-${blockId}`);
  if (el) {
    const out = el.querySelector('.pane-output');
    if (out) out.classList.remove('thinking');
  }
}

function _processQueue() {
  const idleWorkerIndex = workers.findIndex(w => w.idle);
  if (idleWorkerIndex === -1) return;
  if (pendingQueue.size === 0) return;

  const [blockId, req] = pendingQueue.entries().next().value;
  pendingQueue.delete(blockId);

  _dispatchToWorker(idleWorkerIndex, blockId, req.latex, req.sequenceId);
}

function _dispatchToWorker(workerIndex, blockId, latex, seqId) {
  const workerObj = workers[workerIndex];
  workerObj.idle = false;
  
  const block = blocks.find(b => b.id === blockId);
  if (block) {
    block.activeWorkerIndex = workerIndex;
    _setThinkingState(blockId);
    
    if (block.watchdogTimer) clearTimeout(block.watchdogTimer);
    block.watchdogTimer = setTimeout(() => {
      // The Executioner
      console.warn(`Worker ${workerIndex} hung! Terminating and replacing...`);
      workerObj.worker.terminate();
      
      readyCount = Math.max(0, readyCount - 1);
      _createWorker(workerIndex);
      
      _clearThinkingState(blockId);
      block.watchdogTimer = null;
      _showError(blockId, "Computation Timeout: Intractable or too complex.");
      
    }, 5000);
  }
  
  workerObj.worker.postMessage({
    id: seqId,
    blockId: blockId,
    latexInput: latex,
    settings: { assumeReal: settings.assumeReal, useDegrees: settings.useDegrees, precision: settings.precision, stepsMode: settings.stepsMode }
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

  const idleWorkerIndex = workers.findIndex(w => w.idle);
  if (idleWorkerIndex !== -1) {
    _dispatchToWorker(idleWorkerIndex, blockId, latex, requestSequence);
  } else {
    pendingQueue.set(blockId, { latex, sequenceId: requestSequence });
  }
}"""

content = content.replace(worker_pool_old, worker_pool_new)

with open("index.html", "w") as f:
    f.write(content)

print("Patched worker pool logic successfully.")
