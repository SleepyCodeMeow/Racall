const { app, dialog } = require('electron');
const { createRuntime } = require('./runtime.cjs');
const { createBackendService } = require('./backend.cjs');
const { createSecureSession, protectNavigation } = require('./security.cjs');
const {
  initializeTheme,
  createWindow,
  observeTheme,
  protectUnsavedChanges,
} = require('./window.cjs');
const { registerNativeActions } = require('./native-actions.cjs');
const { nativeMessage } = require('./locale.cjs');

// Lifecycle state stays in one place: a cancelled close must keep Python alive.
let window;
let quitting = false;
const runtime = createRuntime(app);
const tr = (key, params) => nativeMessage(runtime.dataDir, key, params);
const backend = createBackendService(runtime, {
  tr,
  onExit() {
    if (!quitting && window) {
      dialog.showErrorBox('Racall', tr('native.stopped', { path: runtime.backendLog }));
      app.quit();
    }
  },
});

async function start() {
  initializeTheme(runtime.dataDir);
  const origin = await backend.start();
  const uiOrigin = process.env.OPENNOTEBOOK_DEV_URL || origin;
  const partition = createSecureSession(origin, runtime.token);
  window = createWindow(partition);
  registerNativeActions({ window, uiOrigin, origin, dataDir: runtime.dataDir });
  observeTheme(window);
  protectNavigation(window, uiOrigin);
  protectUnsavedChanges(window, tr, () => {
    quitting = false;
  });
  await window.loadURL(uiOrigin);
}

if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => {
    if (window) {
      window.restore();
      window.focus();
    }
  });
  app
    .whenReady()
    .then(start)
    .catch((error) => {
      dialog.showErrorBox(tr('native.startTitle'), error.message);
      app.quit();
    });
}
app.on('window-all-closed', () => app.quit());
app.on('before-quit', () => {
  quitting = true;
});
// Keep the service alive if an unsaved editor prevents the window from closing.
app.on('will-quit', () => {
  backend.stop();
});
