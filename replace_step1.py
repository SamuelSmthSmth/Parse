import sys

with open("index.html", "r") as f:
    content = f.read()

# 1. Remove Sidebar HTML
html_to_remove = """    <!-- Settings button & Sidebar -->
    <button id="settings-btn" aria-label="Open settings" aria-expanded="false" aria-controls="settings-panel">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="3"></circle>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
      </svg>
    </button>

    <div id="settings-overlay" aria-hidden="true"></div>

    <aside id="settings-panel" role="dialog" aria-modal="true" aria-label="Settings" aria-hidden="true">
      <div class="settings-header">
        <span class="settings-title">Settings</span>
        <button id="settings-close" aria-label="Close settings">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <div class="settings-section">
        
        <!-- Show Approximations -->
        <div class="settings-row" id="row-show-approx">
          <div class="settings-row-info">
            <span class="settings-row-label">Show Approximations</span>
            <span class="settings-row-desc">decimal ≈ value below result</span>
          </div>
          <label class="toggle" aria-label="Show Approximations">
            <input type="checkbox" id="toggle-approx" />
            <span class="toggle-track"></span>
            <span class="toggle-thumb"></span>
          </label>
        </div>



        <!-- Assumption Tuning — assume all free variables are real -->
        <div class="settings-row" id="row-assumptions">
          <div class="settings-row-info">
            <span class="settings-row-label">Assume Real Variables</span>
            <span class="settings-row-desc">x, y, z treated as ℝ</span>
          </div>
          <label class="toggle" aria-label="Assume Real Variables">
            <input type="checkbox" id="toggle-assumptions" />
            <span class="toggle-track"></span>
            <span class="toggle-thumb"></span>
          </label>
        </div>

      </div>

      <p class="settings-footer">settings auto-saved</p>
    </aside>"""

palette_html = """    <!-- Command Palette -->
    <div id="cmd-overlay" aria-hidden="true">
      <div id="cmd-palette" role="dialog" aria-modal="true" aria-label="Command Palette">
        <input type="text" id="cmd-input" placeholder="Search equations or commands (e.g. Theme, Approx)..." autocomplete="off" spellcheck="false" />
        <ul id="cmd-results" role="listbox"></ul>
      </div>
    </div>"""

if html_to_remove in content:
    content = content.replace(html_to_remove, palette_html)
else:
    print("Could not find HTML to remove.")

# 2. Update CSS
start_css_marker = "/* ════════════════════════════════════════════════════════════════\n       SETTINGS PANEL (Sidebar & Toggles)"
end_css_marker = "    /* ════════════════════════════════════════════════════════════════\n       MAIN LAYOUT"

if start_css_marker in content and end_css_marker in content:
    palette_css = """/* ════════════════════════════════════════════════════════════════
       COMMAND PALETTE
    ════════════════════════════════════════════════════════════════ */
    #cmd-overlay {
      position: fixed;
      inset: 0;
      background: var(--bg-ovl);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      z-index: 1000;
      display: flex;
      align-items: flex-start;
      justify-content: center;
      padding-top: 15vh;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.2s ease;
    }

    #cmd-overlay.open {
      opacity: 1;
      pointer-events: auto;
    }

    #cmd-palette {
      width: 100%;
      max-width: 600px;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.15);
      overflow: hidden;
      transform: translateY(-20px) scale(0.98);
      transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
      display: flex;
      flex-direction: column;
    }

    #cmd-overlay.open #cmd-palette {
      transform: translateY(0) scale(1);
    }

    #cmd-input {
      width: 100%;
      background: transparent;
      border: none;
      border-bottom: 1px solid var(--border);
      padding: 1.25rem 1.5rem;
      font-size: 1.2rem;
      color: var(--fg);
      font-family: var(--sans);
      outline: none;
    }

    #cmd-input::placeholder {
      color: var(--placeholder);
    }

    #cmd-results {
      list-style: none;
      margin: 0;
      padding: 0;
      max-height: 400px;
      overflow-y: auto;
    }

    .cmd-item {
      padding: 1rem 1.5rem;
      cursor: pointer;
      font-family: var(--mono);
      font-size: 1rem;
      color: var(--fg);
      border-left: 3px solid transparent;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .cmd-item:hover, .cmd-item.selected {
      background: var(--pill-subtle);
      border-left-color: var(--caret-col);
    }
    
    .cmd-item-desc {
      font-family: var(--sans);
      font-size: 0.8rem;
      opacity: 0.5;
    }

"""
    start_idx = content.find(start_css_marker)
    end_idx = content.find(end_css_marker)
    content = content[:start_idx] + palette_css + content[end_idx:]
else:
    print("Could not find CSS markers.")

# 3. Update JS
js_remove_start = "/* ════════════════════════════════════════════════════════════════════════\n   SECTION 3 — SETTINGS PANEL"
js_remove_end = "/* ════════════════════════════════════════════════════════════════════════\n   SECTION 4 — NOTEBOOK STATE"

if js_remove_start in content and js_remove_end in content:
    js_cmd_logic = """/* ════════════════════════════════════════════════════════════════════════
   SECTION 3 — COMMAND PALETTE
════════════════════════════════════════════════════════════════════════ */

const cmdOverlay = document.getElementById('cmd-overlay');
const cmdInput   = document.getElementById('cmd-input');
const cmdResults = document.getElementById('cmd-results');
let _cmdOpen = false;
let _cmdSelectedIndex = -1;
let _cmdItems = [];

function _openPalette() {
  _cmdOpen = true;
  cmdOverlay.classList.add('open');
  cmdOverlay.setAttribute('aria-hidden', 'false');
  cmdInput.value = '';
  _renderCmdResults();
  setTimeout(() => cmdInput.focus(), 50); // wait for transition
}

function _closePalette() {
  _cmdOpen = false;
  cmdOverlay.classList.remove('open');
  cmdOverlay.setAttribute('aria-hidden', 'true');
  cmdInput.blur();
  if (activeBlockId) {
    const ta = document.getElementById(`in-${activeBlockId}`);
    if (ta) ta.focus();
  }
}

document.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    _cmdOpen ? _closePalette() : _openPalette();
  }
  if (e.key === 'Escape' && _cmdOpen) {
    e.preventDefault();
    _closePalette();
  }
});

cmdOverlay.addEventListener('mousedown', (e) => {
  if (e.target === cmdOverlay) _closePalette();
});

cmdInput.addEventListener('input', _renderCmdResults);
cmdInput.addEventListener('keydown', (e) => {
  if (!_cmdOpen) return;
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    _cmdSelectedIndex = Math.min(_cmdSelectedIndex + 1, _cmdItems.length - 1);
    _drawCmdSelection();
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    _cmdSelectedIndex = Math.max(_cmdSelectedIndex - 1, 0);
    _drawCmdSelection();
  } else if (e.key === 'Enter') {
    e.preventDefault();
    if (_cmdSelectedIndex >= 0 && _cmdSelectedIndex < _cmdItems.length) {
      _executeCmd(_cmdItems[_cmdSelectedIndex]);
    }
  }
});

function _renderCmdResults() {
  const query = cmdInput.value.toLowerCase().trim();
  _cmdItems = [];

  // Commands
  const cmds = [
    { type: 'cmd', label: 'Theme: Toggle Dark/Light', keywords: 'theme dark light mode color' },
    { type: 'cmd', label: `Settings: Show Approximations (${settings.showApprox ? 'ON' : 'OFF'})`, keywords: 'approx decimal setting' },
    { type: 'cmd', label: `Settings: Assume Real Variables (${settings.assumeReal ? 'ON' : 'OFF'})`, keywords: 'assume real variables setting' }
  ];

  cmds.forEach(cmd => {
    if (!query || cmd.label.toLowerCase().includes(query) || cmd.keywords.includes(query)) {
      _cmdItems.push(cmd);
    }
  });

  // Notebook Blocks
  blocks.forEach(b => {
    if (b.latex && b.latex.trim().length > 0) {
      if (!query || b.latex.toLowerCase().includes(query)) {
        _cmdItems.push({ type: 'block', id: b.id, label: b.latex });
      }
    }
  });

  _cmdSelectedIndex = _cmdItems.length > 0 ? 0 : -1;
  
  cmdResults.innerHTML = '';
  _cmdItems.forEach((item, index) => {
    const li = document.createElement('li');
    li.className = 'cmd-item';
    
    const textSpan = document.createElement('span');
    // truncate overly long latex
    let disp = item.label;
    if (disp.length > 60) disp = disp.substring(0, 58) + '...';
    textSpan.textContent = disp;
    li.appendChild(textSpan);

    const descSpan = document.createElement('span');
    descSpan.className = 'cmd-item-desc';
    descSpan.textContent = item.type === 'cmd' ? 'Command' : 'Equation';
    li.appendChild(descSpan);

    li.addEventListener('mousedown', (e) => {
      e.preventDefault(); // keep focus on input
      _executeCmd(item);
    });
    
    li.addEventListener('mouseenter', () => {
      _cmdSelectedIndex = index;
      _drawCmdSelection();
    });

    cmdResults.appendChild(li);
  });
  
  _drawCmdSelection();
}

function _drawCmdSelection() {
  const items = cmdResults.querySelectorAll('.cmd-item');
  items.forEach((el, idx) => {
    if (idx === _cmdSelectedIndex) {
      el.classList.add('selected');
      el.scrollIntoView({ block: 'nearest' });
    } else {
      el.classList.remove('selected');
    }
  });
}

function _executeCmd(item) {
  _closePalette();
  if (item.type === 'cmd') {
    if (item.label.includes('Theme')) {
      _applyTheme(!isDark);
    } else if (item.label.includes('Approx')) {
      settings.showApprox = !settings.showApprox;
      _lsSave(LS.SHOW_APPROX, settings.showApprox);
      if (!settings.showApprox) {
        blocks.forEach(b => _hideApprox(b.id));
      } else {
        blocks.forEach(b => { if (b.approx) _renderApprox(b.id, b.approx); });
      }
    } else if (item.label.includes('Assume')) {
      settings.assumeReal = !settings.assumeReal;
      _lsSave(LS.ASSUME_REAL, settings.assumeReal);
      if (readyCount === WORKER_COUNT) {
        blocks.forEach(b => { if (b.latex.trim()) sendToWorker(b.id, b.latex); });
      }
    }
  } else if (item.type === 'block') {
    const ta = document.getElementById(`in-${item.id}`);
    if (ta) {
      ta.focus();
      const el = document.getElementById(`block-${item.id}`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
}

"""
    start_idx = content.find(js_remove_start)
    end_idx = content.find(js_remove_end)
    content = content[:start_idx] + js_cmd_logic + content[end_idx:]
else:
    print("Could not find JS markers.")


# Also we need to clean up DOM references in JS section 1:
# Remove settingsBtn, settingsPanel, settingsClose, settingsOvl, toggleApprox
js_dom_refs_to_remove = """const settingsBtn   = document.getElementById('settings-btn');
const settingsPanel = document.getElementById('settings-panel');
const settingsClose = document.getElementById('settings-close');
const settingsOvl   = document.getElementById('settings-overlay');
const toggleApprox  = document.getElementById('toggle-approx');"""

content = content.replace(js_dom_refs_to_remove, "")


# Remove old toggle event listeners in SECTION 1
js_old_toggles_start = "/** Apply settings.showApprox to the toggle UI. */"
js_old_toggles_end = "/* ════════════════════════════════════════════════════════════════════════\n   SECTION 2 — THEME"

if js_old_toggles_start in content and js_old_toggles_end in content:
    start_idx = content.find(js_old_toggles_start)
    end_idx = content.find(js_old_toggles_end)
    content = content[:start_idx] + content[end_idx:]
else:
    print("Could not find old toggles markers.")


with open("index.html", "w") as f:
    f.write(content)

