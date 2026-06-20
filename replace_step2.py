import sys

with open("index.html", "r") as f:
    content = f.read()

# 1. Update CSS
css_old = """    [data-theme="light"] {
      --bg:           #f3f3f7;
      --fg:           #18182a;
      --fg-dim:       rgba(24, 24, 42, 0.22);
      --fg-subtle:    rgba(24, 24, 42, 0.08);
      --divider:      rgba(24, 24, 42, 0.07);
      --caret-col:    #5a48f0;
      --caret-glow:   rgba(90, 72, 240, 0.42);
      --caret-err:    #d03030;
      --caret-err-glow: rgba(208, 48, 48, 0.38);
      --pill-bg:      rgba(0, 0, 0, 0.045);
      --pill-border:  rgba(0, 0, 0, 0.09);
      --err:          #d03030;
      --panel-bg:     rgba(240, 240, 245, 0.92);
      --panel-border: rgba(0, 0, 0, 0.07);
      --toggle-on:    #5a48f0;
    }"""

css_new = css_old + """

    [data-theme="dracula"] {
      --bg:           #282a36;
      --fg:           #f8f8f2;
      --fg-dim:       rgba(248, 248, 242, 0.4);
      --fg-subtle:    rgba(248, 248, 242, 0.15);
      --divider:      rgba(248, 248, 242, 0.1);
      --caret-col:    #bd93f9;
      --caret-glow:   rgba(189, 147, 249, 0.5);
      --caret-err:    #ff5555;
      --caret-err-glow: rgba(255, 85, 85, 0.5);
      --pill-bg:      rgba(255, 255, 255, 0.05);
      --pill-border:  rgba(255, 255, 255, 0.1);
      --err:          #ff5555;
      --panel-bg:     rgba(40, 42, 54, 0.92);
      --panel-border: rgba(255, 255, 255, 0.1);
      --toggle-on:    #bd93f9;
    }

    [data-theme="gruvbox"] {
      --bg:           #282828;
      --fg:           #ebdbb2;
      --fg-dim:       rgba(235, 219, 178, 0.4);
      --fg-subtle:    rgba(235, 219, 178, 0.15);
      --divider:      rgba(235, 219, 178, 0.1);
      --caret-col:    #fabd2f;
      --caret-glow:   rgba(250, 189, 47, 0.5);
      --caret-err:    #fb4934;
      --caret-err-glow: rgba(251, 73, 52, 0.5);
      --pill-bg:      rgba(255, 255, 255, 0.05);
      --pill-border:  rgba(255, 255, 255, 0.1);
      --err:          #fb4934;
      --panel-bg:     rgba(40, 40, 40, 0.92);
      --panel-border: rgba(255, 255, 255, 0.1);
      --toggle-on:    #fabd2f;
    }

    [data-theme="nord"] {
      --bg:           #2e3440;
      --fg:           #eceff4;
      --fg-dim:       rgba(236, 239, 244, 0.4);
      --fg-subtle:    rgba(236, 239, 244, 0.15);
      --divider:      rgba(236, 239, 244, 0.1);
      --caret-col:    #88c0d0;
      --caret-glow:   rgba(136, 192, 208, 0.5);
      --caret-err:    #bf616a;
      --caret-err-glow: rgba(191, 97, 106, 0.5);
      --pill-bg:      rgba(255, 255, 255, 0.05);
      --pill-border:  rgba(255, 255, 255, 0.1);
      --err:          #bf616a;
      --panel-bg:     rgba(46, 52, 64, 0.92);
      --panel-border: rgba(255, 255, 255, 0.1);
      --toggle-on:    #88c0d0;
    }

    [data-theme="matrix"] {
      --bg:           #000000;
      --fg:           #00ff00;
      --fg-dim:       rgba(0, 255, 0, 0.4);
      --fg-subtle:    rgba(0, 255, 0, 0.15);
      --divider:      rgba(0, 255, 0, 0.2);
      --caret-col:    #00ff00;
      --caret-glow:   rgba(0, 255, 0, 0.6);
      --caret-err:    #ff0000;
      --caret-err-glow: rgba(255, 0, 0, 0.6);
      --pill-bg:      rgba(0, 255, 0, 0.05);
      --pill-border:  rgba(0, 255, 0, 0.2);
      --err:          #ff0000;
      --panel-bg:     rgba(0, 0, 0, 0.92);
      --panel-border: rgba(0, 255, 0, 0.2);
      --toggle-on:    #00ff00;
    }"""

if css_old in content:
    content = content.replace(css_old, css_new)
else:
    print("Could not find CSS chunk.")

# 2. Update LS keys
ls_old = """const LS = {
  INPUT: 'parse_input_blocks',
  THEME: 'parse_theme',
  SHOW_APPROX: 'parse_show_approx',
  ASSUME_REAL: 'parse_assume_real'
};"""
ls_new = """const LS = {
  INPUT: 'parse_input_blocks',
  THEME: 'parse_theme',
  SHOW_APPROX: 'parse_show_approx',
  ASSUME_REAL: 'parse_assume_real',
  USE_DEGREES: 'parse_use_degrees',
  PRECISION: 'parse_precision'
};"""
if ls_old in content: content = content.replace(ls_old, ls_new)

# 3. Update settings object
settings_old = """const settings = {
  showApprox:  false,
  assumeReal:  false,   // forwarded to Python via worker postMessage
};"""
settings_new = """const settings = {
  showApprox:  false,
  assumeReal:  false,
  useDegrees:  false,
  precision:   10
};"""
if settings_old in content: content = content.replace(settings_old, settings_new)

# 4. Update _applyTheme
theme_old = """let isDark = true;

function _applyTheme(dark) {
  isDark = dark;
  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  themeBtn.textContent = isDark ? 'Light' : 'Dark';
  _lsSave(LS.THEME, isDark);
}

themeBtn.addEventListener('click', () => _applyTheme(!isDark));"""

theme_new = """let currentTheme = 'dark';

function _applyTheme(theme) {
  if (theme === true) theme = 'dark'; // migration
  if (theme === false) theme = 'light';
  currentTheme = theme;
  document.documentElement.setAttribute('data-theme', theme);
  if (themeBtn) {
    themeBtn.textContent = theme.charAt(0).toUpperCase() + theme.slice(1);
  }
  _lsSave(LS.THEME, theme);
}

if (themeBtn) {
  themeBtn.addEventListener('click', () => {
    _applyTheme(currentTheme === 'dark' ? 'light' : 'dark');
  });
}"""
if theme_old in content: content = content.replace(theme_old, theme_new)

# 5. Focus Restoration
focus_old = """const cmdResults = document.getElementById('cmd-results');
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
}"""

focus_new = """const cmdResults = document.getElementById('cmd-results');
let _cmdOpen = false;
let _cmdSelectedIndex = -1;
let _cmdItems = [];
let _cmdSavedFocus = null;

function _openPalette() {
  _cmdSavedFocus = document.activeElement;
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
  if (_cmdSavedFocus) {
    _cmdSavedFocus.focus();
    _cmdSavedFocus = null;
  }
}"""
if focus_old in content: content = content.replace(focus_old, focus_new)

# 6. Commands logic (cmds array)
render_old = """  // Commands
  const cmds = [
    { type: 'cmd', label: 'Theme: Toggle Dark/Light', keywords: 'theme dark light mode color' },
    { type: 'cmd', label: `Settings: Show Approximations (${settings.showApprox ? 'ON' : 'OFF'})`, keywords: 'approx decimal setting' },
    { type: 'cmd', label: `Settings: Assume Real Variables (${settings.assumeReal ? 'ON' : 'OFF'})`, keywords: 'assume real variables setting' }
  ];"""

render_new = """  // Commands
  const cmds = [
    { type: 'cmd', label: 'Theme: Dark', keywords: 'theme dark mode color' },
    { type: 'cmd', label: 'Theme: Light', keywords: 'theme light mode color' },
    { type: 'cmd', label: 'Theme: Dracula', keywords: 'theme dracula mode color' },
    { type: 'cmd', label: 'Theme: Gruvbox', keywords: 'theme gruvbox mode color' },
    { type: 'cmd', label: 'Theme: Nord', keywords: 'theme nord mode color' },
    { type: 'cmd', label: 'Theme: Matrix', keywords: 'theme matrix mode color hacker' },
    { type: 'cmd', label: `Settings: Show Approximations (${settings.showApprox ? 'ON' : 'OFF'})`, keywords: 'approx decimal setting' },
    { type: 'cmd', label: `Settings: Assume Real Variables (${settings.assumeReal ? 'ON' : 'OFF'})`, keywords: 'assume real variables setting' },
    { type: 'cmd', label: `Settings: Toggle Angles (${settings.useDegrees ? 'Degrees' : 'Radians'})`, keywords: 'angle degree radian setting' },
    { type: 'cmd', label: `Settings: Set Precision: 10`, keywords: 'precision decimals' },
    { type: 'cmd', label: `Clear Notebook`, keywords: 'clear notebook empty delete' }
  ];"""
if render_old in content: content = content.replace(render_old, render_new)

# 7. Execute cmd
exec_old = """function _executeCmd(item) {
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
  } else if (item.type === 'block') {"""

exec_new = """function _executeCmd(item) {
  _closePalette();
  if (item.type === 'cmd') {
    if (item.label.includes('Theme:')) {
      const theme = item.label.split('Theme: ')[1].toLowerCase();
      _applyTheme(theme);
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
    } else if (item.label.includes('Toggle Angles')) {
      settings.useDegrees = !settings.useDegrees;
      _lsSave(LS.USE_DEGREES, settings.useDegrees);
      if (readyCount === WORKER_COUNT) {
        blocks.forEach(b => { if (b.latex.trim()) sendToWorker(b.id, b.latex); });
      }
    } else if (item.label.includes('Set Precision: 10')) {
      settings.precision = 10;
      _lsSave(LS.PRECISION, settings.precision);
      if (readyCount === WORKER_COUNT) {
        blocks.forEach(b => { if (b.latex.trim()) sendToWorker(b.id, b.latex); });
      }
    } else if (item.label.includes('Clear Notebook')) {
      blocks.slice().forEach(b => {
        const el = document.getElementById(`block-${b.id}`);
        if (el) el.remove();
      });
      blocks = [];
      _saveNotebook();
      _createBlock('', null, true);
    }
  } else if (item.type === 'block') {"""
if exec_old in content: content = content.replace(exec_old, exec_new)

# 8. Worker message
worker_old = """      settings: { assumeReal: settings.assumeReal }"""
worker_new = """      settings: { assumeReal: settings.assumeReal, useDegrees: settings.useDegrees, precision: settings.precision }"""
content = content.replace(worker_old, worker_new)

# 9. Init state
init_old = """(function init() {
  const savedTheme = _lsLoad(LS.THEME, true);
  _applyTheme(savedTheme);

  settings.showApprox = _lsLoad(LS.SHOW_APPROX, false);
  settings.assumeReal = _lsLoad(LS.ASSUME_REAL, false);"""
init_new = """(function init() {
  const savedTheme = _lsLoad(LS.THEME, 'dark');
  _applyTheme(savedTheme);

  settings.showApprox = _lsLoad(LS.SHOW_APPROX, false);
  settings.assumeReal = _lsLoad(LS.ASSUME_REAL, false);
  settings.useDegrees = _lsLoad(LS.USE_DEGREES, false);
  settings.precision  = _lsLoad(LS.PRECISION, 10);"""
if init_old in content: content = content.replace(init_old, init_new)

with open("index.html", "w") as f:
    f.write(content)

