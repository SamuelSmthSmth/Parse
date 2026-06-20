import sys

with open("index.html", "r") as f:
    content = f.read()

# 1. State
state_old = """let _cmdSelectedIndex = -1;
let _cmdItems = [];
let _cmdSavedFocus = null;"""
state_new = """let _cmdSelectedIndex = -1;
let _cmdItems = [];
let _cmdSavedFocus = null;
let _cmdCurrentMenu = 'root';"""
content = content.replace(state_old, state_new)

# 2. openPalette
open_old = """function _openPalette() {
  _cmdSavedFocus = document.activeElement;
  _cmdOpen = true;
  cmdOverlay.classList.add('open');
  cmdOverlay.setAttribute('aria-hidden', 'false');
  cmdInput.value = '';
  _renderCmdResults();"""
open_new = """function _openPalette() {
  _cmdSavedFocus = document.activeElement;
  _cmdOpen = true;
  _cmdCurrentMenu = 'root';
  cmdOverlay.classList.add('open');
  cmdOverlay.setAttribute('aria-hidden', 'false');
  cmdInput.value = '';
  _renderCmdResults();"""
content = content.replace(open_old, open_new)

# 3. keydown for backspace
key_old = """cmdInput.addEventListener('keydown', (e) => {
  if (!_cmdOpen) return;
  if (e.key === 'ArrowDown') {"""
key_new = """cmdInput.addEventListener('keydown', (e) => {
  if (!_cmdOpen) return;
  if (e.key === 'Backspace' && cmdInput.value === '' && _cmdCurrentMenu !== 'root') {
    e.preventDefault();
    _cmdCurrentMenu = 'root';
    _renderCmdResults();
    return;
  }
  if (e.key === 'ArrowDown') {"""
content = content.replace(key_old, key_new)

# 4. _renderCmdResults
render_old = """function _renderCmdResults() {
  const query = cmdInput.value.toLowerCase().trim();
  _cmdItems = [];

  // Commands
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

  _cmdSelectedIndex = _cmdItems.length > 0 ? 0 : -1;"""
render_new = """function _renderCmdResults() {
  const query = cmdInput.value.toLowerCase().trim();
  _cmdItems = [];

  if (_cmdCurrentMenu === 'root') {
    cmdInput.placeholder = "Search commands or equations...";
    const rootCmds = [
      { type: 'menu', id: 'themes', label: 'Themes...', keywords: 'theme color dark light' },
      { type: 'menu', id: 'settings', label: 'Settings...', keywords: 'settings approx assume angle precision' },
      { type: 'cmd', label: `Clear Notebook`, keywords: 'clear notebook empty delete' }
    ];
    rootCmds.forEach(cmd => {
      if (!query || cmd.label.toLowerCase().includes(query) || cmd.keywords.includes(query)) _cmdItems.push(cmd);
    });
    blocks.forEach(b => {
      if (b.latex && b.latex.trim().length > 0) {
        if (!query || b.latex.toLowerCase().includes(query)) {
          _cmdItems.push({ type: 'block', id: b.id, label: b.latex });
        }
      }
    });
  } else if (_cmdCurrentMenu === 'themes') {
    cmdInput.placeholder = "Search themes...";
    _cmdItems.push({ type: 'back', label: '< Back to Main Menu', keywords: '' });
    const themes = [
      { type: 'cmd', label: 'Theme: Dark', keywords: 'dark' },
      { type: 'cmd', label: 'Theme: Light', keywords: 'light' },
      { type: 'cmd', label: 'Theme: Dracula', keywords: 'dracula' },
      { type: 'cmd', label: 'Theme: Gruvbox', keywords: 'gruvbox' },
      { type: 'cmd', label: 'Theme: Nord', keywords: 'nord' },
      { type: 'cmd', label: 'Theme: Matrix', keywords: 'matrix hacker' }
    ];
    themes.forEach(cmd => {
      if (!query || cmd.label.toLowerCase().includes(query) || cmd.keywords.includes(query)) _cmdItems.push(cmd);
    });
  } else if (_cmdCurrentMenu === 'settings') {
    cmdInput.placeholder = "Search settings...";
    _cmdItems.push({ type: 'back', label: '< Back to Main Menu', keywords: '' });
    const settingsCmds = [
      { type: 'cmd', label: `Settings: Show Approximations (${settings.showApprox ? 'ON' : 'OFF'})`, keywords: 'approx decimal setting' },
      { type: 'cmd', label: `Settings: Assume Real Variables (${settings.assumeReal ? 'ON' : 'OFF'})`, keywords: 'assume real variables setting' },
      { type: 'cmd', label: `Settings: Toggle Angles (${settings.useDegrees ? 'Degrees' : 'Radians'})`, keywords: 'angle degree radian setting' },
      { type: 'cmd', label: `Settings: Set Precision: 10`, keywords: 'precision decimals' }
    ];
    settingsCmds.forEach(cmd => {
      if (!query || cmd.label.toLowerCase().includes(query) || cmd.keywords.includes(query)) _cmdItems.push(cmd);
    });
  }

  _cmdSelectedIndex = _cmdItems.length > 0 ? 0 : -1;"""
content = content.replace(render_old, render_new)

# 5. descSpan in _renderCmdResults
desc_old = """    descSpan.textContent = item.type === 'cmd' ? 'Command' : 'Equation';"""
desc_new = """    descSpan.textContent = item.type === 'menu' ? 'Menu' : item.type === 'back' ? 'Back' : item.type === 'cmd' ? 'Command' : 'Equation';"""
content = content.replace(desc_old, desc_new)

# 6. _executeCmd
exec_old = """function _executeCmd(item) {
  _closePalette();
  if (item.type === 'cmd') {"""
exec_new = """function _executeCmd(item) {
  if (item.type === 'menu') {
    _cmdCurrentMenu = item.id;
    cmdInput.value = '';
    _renderCmdResults();
    return;
  } else if (item.type === 'back') {
    _cmdCurrentMenu = 'root';
    cmdInput.value = '';
    _renderCmdResults();
    return;
  }
  
  _closePalette();
  if (item.type === 'cmd') {"""
content = content.replace(exec_old, exec_new)

with open("index.html", "w") as f:
    f.write(content)

