import sys

with open("index.html", "r") as f:
    content = f.read()

# 1. CSS
css_inject = """    .plot-container .origin { stroke: var(--fg-subtle) !important; }
    
    /* Sliders */
    .sliders-container {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      margin-top: 1rem;
      width: 100%;
      max-width: 400px;
    }
    .slider-wrapper {
      display: flex;
      align-items: center;
      gap: 1rem;
    }
    .slider-wrapper span {
      font-family: var(--mono);
      font-size: 0.9em;
      color: var(--fg);
      min-width: 4rem;
    }
    input[type=range] {
      -webkit-appearance: none;
      width: 100%;
      background: transparent;
    }
    input[type=range]::-webkit-slider-thumb {
      -webkit-appearance: none;
      height: 14px;
      width: 14px;
      border-radius: 50%;
      background: var(--caret-col);
      cursor: pointer;
      margin-top: -6px;
    }
    input[type=range]::-webkit-slider-runnable-track {
      width: 100%;
      height: 2px;
      cursor: pointer;
      background: var(--divider);
      border-radius: 2px;
    }"""
content = content.replace("    .plot-container .origin { stroke: var(--fg-subtle) !important; }", css_inject)

# 2. Global variables
global_var = """let globalVariables = {};

// Queue for pending requests when all workers are busy"""
content = content.replace("// Queue for pending requests when all workers are busy", global_var)

# 3. Context passing in sendToWorker -> _dispatchToWorker
old_dispatch = """  workerObj.worker.postMessage({
    id: seqId,
    blockId: blockId,
    latexInput: latex,
    settings: { assumeReal: settings.assumeReal, useDegrees: settings.useDegrees, precision: settings.precision, stepsMode: settings.stepsMode }
  });"""

new_dispatch = """  const contextData = { ...globalVariables, ...(block.sliderOverrides || {}) };
  workerObj.worker.postMessage({
    id: seqId,
    blockId: blockId,
    latexInput: latex,
    settings: { 
      assumeReal: settings.assumeReal, 
      useDegrees: settings.useDegrees, 
      precision: settings.precision, 
      stepsMode: settings.stepsMode,
      context: contextData
    }
  });"""
content = content.replace(old_dispatch, new_dispatch)

# 4. _handleWorkerResponse
old_handle = """    if (data.status === 'success') {
      _clearErrorGlow();"""

new_handle = """    if (data.status === 'success') {
      _clearErrorGlow();
      
      if (data.new_assignment) {
        globalVariables[data.new_assignment.key] = data.new_assignment.val;
      }
      
      const blockEl = document.getElementById(`block-${block.id}`);
      let sliderContainer = blockEl ? blockEl.querySelector('.sliders-container') : null;
      
      if (data.free_symbols && data.free_symbols.length > 0 && blockEl) {
        if (!sliderContainer) {
          sliderContainer = document.createElement('div');
          sliderContainer.className = 'sliders-container';
          blockEl.querySelector('.pane-output').appendChild(sliderContainer);
        }
        
        const currentSymbols = sliderContainer.dataset.symbols || '';
        const newSymbols = data.free_symbols.join(',');
        
        if (currentSymbols !== newSymbols) {
          sliderContainer.dataset.symbols = newSymbols;
          sliderContainer.innerHTML = '';
          
          data.free_symbols.forEach(sym => {
            const wrapper = document.createElement('div');
            wrapper.className = 'slider-wrapper';
            
            const initialVal = block.sliderOverrides && block.sliderOverrides[sym] !== undefined ? block.sliderOverrides[sym] : 1;
            
            const label = document.createElement('span');
            label.textContent = `${sym} = ${initialVal}`;
            
            const input = document.createElement('input');
            input.type = 'range';
            input.min = 1;
            input.max = 10;
            input.step = 0.1;
            input.value = initialVal;
            
            input.oninput = (e) => {
              label.textContent = `${sym} = ${e.target.value}`;
              if (!block.sliderOverrides) block.sliderOverrides = {};
              block.sliderOverrides[sym] = e.target.value;
              
              if (block.sliderTimeout) clearTimeout(block.sliderTimeout);
              block.sliderTimeout = setTimeout(() => {
                sendToWorker(block.id, block.latex);
              }, 50);
            };
            
            wrapper.appendChild(label);
            wrapper.appendChild(input);
            sliderContainer.appendChild(wrapper);
          });
        }
      } else if (sliderContainer) {
        sliderContainer.remove();
      }
"""
content = content.replace(old_handle, new_handle)

with open("index.html", "w") as f:
    f.write(content)

print("Patched JS global state successfully.")
