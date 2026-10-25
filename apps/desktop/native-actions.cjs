const { ipcMain, shell, clipboard } = require('electron');
const path = require('node:path');
const { assertTrustedSender } = require('./security.cjs');
const { setWindowTheme } = require('./window.cjs');
const launchers = require('../shared/launchers.json');

/** Expose fixed native capabilities; renderer input never becomes a shell command. */
function registerNativeActions({ window, uiOrigin, origin, dataDir }) {
  const trusted = (event) => assertTrustedSender(event, window, uiOrigin);
  ipcMain.handle('connection', (event) => {
    trusted(event);
    return { origin };
  });
  ipcMain.handle('open-vault', (event) => {
    trusted(event);
    return shell.openPath(path.join(dataDir, 'notebooks'));
  });
  ipcMain.handle('copy-launch-command', (event, integration) => {
    trusted(event);
    if (typeof integration !== 'string' || !launchers.some((item) => item.id === integration)) {
      throw new Error('Unknown launch integration');
    }
    return clipboard.writeText(`ollama launch ${integration}`);
  });
  ipcMain.handle('set-theme', (event, theme) => {
    trusted(event);
    if (!['light', 'dark', 'system'].includes(theme)) throw new Error('Invalid theme');
    setWindowTheme(window, theme);
  });
}

module.exports = { registerNativeActions };
