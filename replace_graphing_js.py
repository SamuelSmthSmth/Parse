import sys

with open("index.html", "r") as f:
    content = f.read()

# 1. Inject script
old_script = """<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js" crossorigin="anonymous"></script>"""
new_script = """<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js" crossorigin="anonymous"></script>
  <script src="https://unpkg.com/function-plot/dist/function-plot.js"></script>"""
content = content.replace(old_script, new_script)

# 2. Add CSS
old_css = """    .pane-output.thinking {
      opacity: 0.5;
      animation: pulse-thinking 1.5s infinite ease-in-out;
      pointer-events: none;
    }"""
new_css = """    .pane-output.thinking {
      opacity: 0.5;
      animation: pulse-thinking 1.5s infinite ease-in-out;
      pointer-events: none;
    }
    
    /* Graphing / Plot Overrides */
    .plot-container {
      width: 100%;
      display: flex;
      justify-content: center;
      margin-top: 1.5rem;
    }
    .plot-container svg {
      background: transparent !important;
      width: 100% !important;
      max-width: 500px;
      height: auto !important;
    }
    .plot-container .domain { stroke: transparent !important; }
    .plot-container .tick line { display: none !important; }
    .plot-container .tick text { fill: var(--fg-dim) !important; font-family: var(--mono); }
    .plot-container .origin { stroke: var(--fg-subtle) !important; }"""
content = content.replace(old_css, new_css)

# 3. DOM string in _createBlock
old_dom = """      <div id="steps-toggle-${id}" class="steps-toggle" style="display:none;" onclick="_toggleSteps('${id}')"></div>
      <div id="steps-container-${id}" class="steps-container"></div>
    </div>"""
new_dom = """      <div id="steps-toggle-${id}" class="steps-toggle" style="display:none;" onclick="_toggleSteps('${id}')"></div>
      <div id="steps-container-${id}" class="steps-container"></div>
      <div id="plot-container-${id}" class="plot-container" style="display:none;"></div>
    </div>"""
content = content.replace(old_dom, new_dom)

# 4. _handleWorkerResponse
old_handle = """    if (data.steps && data.steps.length > 0 && stepsToggle && stepsContainer) {
      stepsToggle.style.display = 'block';
      stepsToggle.textContent = `[+] Show Steps (${data.steps.length})`;
      stepsContainer.innerHTML = '';
      data.steps.forEach(stepLatex => {
        const stepDiv = document.createElement('div');
        stepDiv.className = 'step-item';
        katex.render(stepLatex, stepDiv, { displayMode: true, throwOnError: false });
        stepsContainer.appendChild(stepDiv);
      });
    } else if (stepsToggle && stepsContainer) {
      stepsToggle.style.display = 'none';
      stepsContainer.classList.remove('open');
      stepsContainer.innerHTML = '';
    }
  } else if (data.status === 'error') {"""

new_handle = """    if (data.steps && data.steps.length > 0 && stepsToggle && stepsContainer) {
      stepsToggle.style.display = 'block';
      stepsToggle.textContent = `[+] Show Steps (${data.steps.length})`;
      stepsContainer.innerHTML = '';
      data.steps.forEach(stepLatex => {
        const stepDiv = document.createElement('div');
        stepDiv.className = 'step-item';
        katex.render(stepLatex, stepDiv, { displayMode: true, throwOnError: false });
        stepsContainer.appendChild(stepDiv);
      });
    } else if (stepsToggle && stepsContainer) {
      stepsToggle.style.display = 'none';
      stepsContainer.classList.remove('open');
      stepsContainer.innerHTML = '';
    }

    const plotContainer = document.getElementById(`plot-container-${block.id}`);
    if (data.plot && plotContainer) {
      plotContainer.style.display = 'flex';
      plotContainer.innerHTML = '';
      // Read active theme accent color
      const accentColor = getComputedStyle(document.documentElement).getPropertyValue('--caret-col').trim() || '#8b78ff';
      
      let xDomain = [-10, 10];
      if (data.plot.bounds) {
        const span = Math.abs(data.plot.bounds[1] - data.plot.bounds[0]);
        const pad = Math.max(span * 0.2, 1);
        xDomain = [data.plot.bounds[0] - pad, data.plot.bounds[1] + pad];
      }
      
      try {
        functionPlot({
          target: `#plot-container-${block.id}`,
          width: 500,
          height: 250,
          grid: false,
          xAxis: { domain: xDomain },
          data: [{
            fn: data.plot.fn,
            color: accentColor,
            range: data.plot.bounds || undefined,
            closed: data.plot.bounds ? true : false
          }]
        });
      } catch (err) {
        console.error("Plot error", err);
      }
    } else if (plotContainer) {
      plotContainer.style.display = 'none';
      plotContainer.innerHTML = '';
    }
  } else if (data.status === 'error') {"""
content = content.replace(old_handle, new_handle)

# 5. Fix Error Message String
content = content.replace('"Computation Timeout: Intractable or too complex."', '"Computation Timeout: Expression intractable."')

with open("index.html", "w") as f:
    f.write(content)

print("Patched JS graphing engine logic successfully.")
