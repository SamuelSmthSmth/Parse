import sys

with open("index.html", "r") as f:
    content = f.read()

# 1. LS updates
ls_old = """const LS = {
  INPUT: 'parse_input_blocks',
  THEME: 'parse_theme',
  SHOW_APPROX: 'parse_show_approx',
  ASSUME_REAL: 'parse_assume_real',
  USE_DEGREES: 'parse_use_degrees',
  PRECISION: 'parse_precision'
};"""
ls_new = """const LS = {
  INPUT: 'parse_input_blocks',
  THEME: 'parse_theme',
  SHOW_APPROX: 'parse_show_approx',
  ASSUME_REAL: 'parse_assume_real',
  USE_DEGREES: 'parse_use_degrees',
  PRECISION: 'parse_precision',
  STEPS_MODE: 'parse_steps_mode'
};"""
if ls_old in content: content = content.replace(ls_old, ls_new)

# 2. settings updates
settings_old = """const settings = {
  showApprox:  false,
  assumeReal:  false,
  useDegrees:  false,
  precision:   10
};"""
settings_new = """const settings = {
  showApprox:  false,
  assumeReal:  false,
  useDegrees:  false,
  precision:   10,
  stepsMode:   'off'
};"""
if settings_old in content: content = content.replace(settings_old, settings_new)

# 3. init updates
init_old = """  settings.showApprox = _lsLoad(LS.SHOW_APPROX, false);
  settings.assumeReal = _lsLoad(LS.ASSUME_REAL, false);
  settings.useDegrees = _lsLoad(LS.USE_DEGREES, false);
  settings.precision  = _lsLoad(LS.PRECISION, 10);"""
init_new = """  settings.showApprox = _lsLoad(LS.SHOW_APPROX, false);
  settings.assumeReal = _lsLoad(LS.ASSUME_REAL, false);
  settings.useDegrees = _lsLoad(LS.USE_DEGREES, false);
  settings.precision  = _lsLoad(LS.PRECISION, 10);
  settings.stepsMode  = _lsLoad(LS.STEPS_MODE, 'off');"""
if init_old in content: content = content.replace(init_old, init_new)

# 4. _renderCmdResults updates
render_old = """      { type: 'cmd', label: `Settings: Toggle Angles (${settings.useDegrees ? 'Degrees' : 'Radians'})`, keywords: 'angle degree radian setting' },
      { type: 'cmd', label: `Settings: Set Precision: 10`, keywords: 'precision decimals' }"""
render_new = """      { type: 'cmd', label: `Settings: Toggle Angles (${settings.useDegrees ? 'Degrees' : 'Radians'})`, keywords: 'angle degree radian setting' },
      { type: 'cmd', label: `Settings: Set Precision: 10`, keywords: 'precision decimals' },
      { type: 'cmd', label: `Settings: Steps Mode (${settings.stepsMode})`, keywords: 'steps mode raw friendly off' }"""
if render_old in content: content = content.replace(render_old, render_new)

# 5. _executeCmd updates
exec_old = """    } else if (item.label.includes('Set Precision: 10')) {
      settings.precision = 10;
      _lsSave(LS.PRECISION, settings.precision);
      if (readyCount === WORKER_COUNT) {
        blocks.forEach(b => { if (b.latex.trim()) sendToWorker(b.id, b.latex); });
      }
    } else if (item.label.includes('Clear Notebook')) {"""
exec_new = """    } else if (item.label.includes('Set Precision: 10')) {
      settings.precision = 10;
      _lsSave(LS.PRECISION, settings.precision);
      if (readyCount === WORKER_COUNT) {
        blocks.forEach(b => { if (b.latex.trim()) sendToWorker(b.id, b.latex); });
      }
    } else if (item.label.includes('Steps Mode')) {
      const modes = ['off', 'raw', 'friendly'];
      let idx = modes.indexOf(settings.stepsMode);
      settings.stepsMode = modes[(idx + 1) % 3];
      _lsSave(LS.STEPS_MODE, settings.stepsMode);
      if (readyCount === WORKER_COUNT) {
        blocks.forEach(b => { if (b.latex.trim()) sendToWorker(b.id, b.latex); });
      }
    } else if (item.label.includes('Clear Notebook')) {"""
if exec_old in content: content = content.replace(exec_old, exec_new)

# 6. worker settings
worker_old = """settings: { assumeReal: settings.assumeReal, useDegrees: settings.useDegrees, precision: settings.precision }"""
worker_new = """settings: { assumeReal: settings.assumeReal, useDegrees: settings.useDegrees, precision: settings.precision, stepsMode: settings.stepsMode }"""
content = content.replace(worker_old, worker_new)

# 7. DOM block creation
dom_old = """      <div id="approx-${blockId}" class="approx-output" aria-live="polite"></div>
    </section>
  `;"""
dom_new = """      <div id="approx-${blockId}" class="approx-output" aria-live="polite"></div>
      <div id="steps-toggle-${blockId}" class="steps-toggle" style="display:none;" onclick="_toggleSteps('${blockId}')"></div>
      <div id="steps-container-${blockId}" class="steps-container"></div>
    </section>
  `;"""
if dom_old in content: content = content.replace(dom_old, dom_new)

# 8. receiveFromWorker rendering of steps
rcv_old = """    if (data.approx) {
      block.approx = data.approx;
      if (settings.showApprox) _renderApprox(block.id, data.approx);
    } else {
      block.approx = null;
      _hideApprox(block.id);
    }
  } else if (data.status === 'incomplete') {"""
rcv_new = """    if (data.approx) {
      block.approx = data.approx;
      if (settings.showApprox) _renderApprox(block.id, data.approx);
    } else {
      block.approx = null;
      _hideApprox(block.id);
    }
    
    const stepsToggle = document.getElementById(`steps-toggle-${block.id}`);
    const stepsContainer = document.getElementById(`steps-container-${block.id}`);
    if (data.steps && data.steps.length > 0 && stepsToggle && stepsContainer) {
      stepsToggle.style.display = 'block';
      stepsToggle.textContent = `[+] Show Steps (${data.steps.length})`;
      stepsContainer.innerHTML = '';
      data.steps.forEach(stepLatex => {
        const stepEl = document.createElement('div');
        stepEl.className = 'step-item';
        katex.render(stepLatex, stepEl, { displayMode: true, throwOnError: false });
        stepsContainer.appendChild(stepEl);
      });
    } else if (stepsToggle && stepsContainer) {
      stepsToggle.style.display = 'none';
      stepsContainer.innerHTML = '';
      stepsContainer.classList.remove('open');
    }
  } else if (data.status === 'incomplete') {"""
if rcv_old in content: content = content.replace(rcv_old, rcv_new)

# 9. _toggleSteps function
toggle_func = """
function _toggleSteps(blockId) {
  const container = document.getElementById(`steps-container-${blockId}`);
  const toggle = document.getElementById(`steps-toggle-${blockId}`);
  if (!container || !toggle) return;
  const isOpen = container.classList.contains('open');
  if (isOpen) {
    container.classList.remove('open');
    toggle.textContent = toggle.textContent.replace('[-]', '[+]').replace('Hide', 'Show');
  } else {
    container.classList.add('open');
    toggle.textContent = toggle.textContent.replace('[+]', '[-]').replace('Show', 'Hide');
  }
}
"""
content = content.replace("function _esc(s) {", toggle_func + "\nfunction _esc(s) {")

# 10. CSS updates
css_old = """    .cmd-item-desc {
      font-size: 0.75rem;
      color: var(--fg-subtle);
    }"""
css_new = """    .cmd-item-desc {
      font-size: 0.75rem;
      color: var(--fg-subtle);
    }
    
    .steps-toggle {
      font-family: var(--sans);
      font-size: 0.8rem;
      color: var(--fg-dim);
      cursor: pointer;
      user-select: none;
      margin-top: 0.5rem;
      transition: color 0.2s var(--ease);
      text-align: center;
    }
    .steps-toggle:hover {
      color: var(--fg);
    }
    .steps-container {
      max-height: 0;
      overflow: hidden;
      opacity: 0;
      transition: max-height 0.4s var(--ease), opacity 0.4s var(--ease), margin-top 0.4s var(--ease);
      display: flex;
      flex-direction: column;
      gap: 0.8rem;
    }
    .steps-container.open {
      max-height: 1000px;
      opacity: 1;
      margin-top: 1rem;
    }
    .step-item {
      font-size: 0.95em;
      color: var(--fg-dim);
    }"""
if css_old in content: content = content.replace(css_old, css_new)


with open("index.html", "w") as f:
    f.write(content)

