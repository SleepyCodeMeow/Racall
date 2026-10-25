const { BrowserWindow, dialog, nativeTheme } = require('electron');
const path = require('node:path');
const fs = require('node:fs');

function savedTheme(dataDir) {
  try {
    const theme = JSON.parse(fs.readFileSync(path.join(dataDir, 'appearance.json'), 'utf8')).theme;
    return ['light', 'dark', 'system'].includes(theme) ? theme : 'light';
  } catch {
    return 'light';
  }
}

function themeBackground() {
  return nativeTheme.shouldUseDarkColors ? '#171717' : '#ffffff';
}

function initializeTheme(dataDir) {
  nativeTheme.themeSource = savedTheme(dataDir);
}

function createWindow(partition) {
  return new BrowserWindow({
    width: 1440,
    height: 940,
    minWidth: 1000,
    minHeight: 680,
    show: process.env.OPENNOTEBOOK_SMOKE_MODE !== '1',
    title: 'Racall',
    backgroundColor: themeBackground(),
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      session: partition,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
    },
  });
}

function setWindowTheme(window, theme) {
  nativeTheme.themeSource = theme;
  window.setBackgroundColor(themeBackground());
}

function observeTheme(window) {
  nativeTheme.on('updated', () => {
    if (window && !window.isDestroyed()) window.setBackgroundColor(themeBackground());
  });
}

/** Let the renderer report unsaved edits; only a native dialog can override them. */
function protectUnsavedChanges(window, tr, onKeepEditing) {
  window.webContents.on('will-prevent-unload', (event) => {
    const choice = dialog.showMessageBoxSync(window, {
      type: 'warning',
      title: 'Racall',
      message: tr('native.unsavedTitle'),
      detail: tr('native.unsavedDetail'),
      buttons: [tr('native.keepEditing'), tr('native.closeAnyway')],
      defaultId: 0,
      cancelId: 0,
      noLink: true,
    });
    if (choice === 1) event.preventDefault();
    else onKeepEditing();
  });
}

module.exports = {
  initializeTheme,
  createWindow,
  setWindowTheme,
  observeTheme,
  protectUnsavedChanges,
};
