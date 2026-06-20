import sys

with open("index.html", "r") as f:
    content = f.read()

# 1. Update rootCmds
root_old = """  if (_cmdCurrentMenu === 'root') {
    cmdInput.placeholder = "Search commands or equations...";
    const rootCmds = [
      { type: 'menu', id: 'themes', label: 'Themes...', keywords: 'theme color dark light' },
      { type: 'menu', id: 'settings', label: 'Settings...', keywords: 'settings approx assume angle precision' },
      { type: 'cmd', label: `Clear Notebook`, keywords: 'clear notebook empty delete' }
    ];"""
root_new = """  if (_cmdCurrentMenu === 'root') {
    cmdInput.placeholder = "Search commands or equations...";
    const rootCmds = [
      { type: 'menu', id: 'themes', label: 'Themes...', keywords: 'theme color dark light' },
      { type: 'menu', id: 'settings', label: 'Settings...', keywords: 'settings approx assume angle precision' },
      { type: 'menu', id: 'steps_mode', label: 'Steps Mode...', keywords: 'steps mode friendly raw off' },
      { type: 'cmd', label: `Clear Notebook`, keywords: 'clear notebook empty delete' }
    ];"""
content = content.replace(root_old, root_new)

# 2. Update settings menu to remove the old steps mode, and add steps_mode submenu
settings_old = """      { type: 'cmd', label: `Settings: Set Precision: 10`, keywords: 'precision decimals' },
      { type: 'cmd', label: `Settings: Steps Mode (${settings.stepsMode})`, keywords: 'steps mode raw friendly off' }
    ];
    settingsCmds.forEach(cmd => {
      if (!query || cmd.label.toLowerCase().includes(query) || cmd.keywords.includes(query)) _cmdItems.push(cmd);
    });
  }

  _cmdSelectedIndex = _cmdItems.length > 0 ? 0 : -1;"""
settings_new = """      { type: 'cmd', label: `Settings: Set Precision: 10`, keywords: 'precision decimals' }
    ];
    settingsCmds.forEach(cmd => {
      if (!query || cmd.label.toLowerCase().includes(query) || cmd.keywords.includes(query)) _cmdItems.push(cmd);
    });
  } else if (_cmdCurrentMenu === 'steps_mode') {
    cmdInput.placeholder = "Search steps mode...";
    _cmdItems.push({ type: 'back', label: '< Back to Main Menu', keywords: '' });
    const stepsCmds = [
      { type: 'cmd', label: `Steps Mode: Off${settings.stepsMode === 'off' ? ' (Active)' : ''}`, keywords: 'off disabled' },
      { type: 'cmd', label: `Steps Mode: Raw${settings.stepsMode === 'raw' ? ' (Active)' : ''}`, keywords: 'raw internal ast' },
      { type: 'cmd', label: `Steps Mode: Friendly${settings.stepsMode === 'friendly' ? ' (Active)' : ''}`, keywords: 'friendly tutor manual' }
    ];
    stepsCmds.forEach(cmd => {
      if (!query || cmd.label.toLowerCase().includes(query) || cmd.keywords.includes(query)) _cmdItems.push(cmd);
    });
  }

  _cmdSelectedIndex = _cmdItems.length > 0 ? 0 : -1;"""
content = content.replace(settings_old, settings_new)

# 3. Update _executeCmd
exec_old = """    } else if (item.label.includes('Steps Mode')) {
      const modes = ['off', 'raw', 'friendly'];
      let idx = modes.indexOf(settings.stepsMode);
      settings.stepsMode = modes[(idx + 1) % 3];
      _lsSave(LS.STEPS_MODE, settings.stepsMode);
      if (readyCount === WORKER_COUNT) {
        blocks.forEach(b => { if (b.latex.trim()) sendToWorker(b.id, b.latex); });
      }
    } else if (item.label.includes('Clear Notebook')) {"""
exec_new = """    } else if (item.label.includes('Steps Mode:')) {
      if (item.label.includes('Off')) {
        settings.stepsMode = 'off';
      } else if (item.label.includes('Raw')) {
        settings.stepsMode = 'raw';
      } else if (item.label.includes('Friendly')) {
        settings.stepsMode = 'friendly';
      }
      _lsSave(LS.STEPS_MODE, settings.stepsMode);
      if (readyCount === WORKER_COUNT) {
        blocks.forEach(b => { if (b.latex.trim()) sendToWorker(b.id, b.latex); });
      }
    } else if (item.label.includes('Clear Notebook')) {"""
content = content.replace(exec_old, exec_new)

with open("index.html", "w") as f:
    f.write(content)

