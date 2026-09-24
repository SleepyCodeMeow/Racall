const { app, BrowserWindow, session, ipcMain, dialog, shell } = require('electron');
const { spawn } = require('node:child_process');
const { randomBytes } = require('node:crypto');
const { createServer } = require('node:net');
const path = require('node:path');
const fs = require('node:fs');
const { initializeLocale, nativeMessage } = require('./locale.cjs');

let backend;
let window;
let quitting = false;
let origin;
const root = path.resolve(__dirname, '../..');
// Branding must not move existing notebooks or provider settings.
app.setPath('userData', path.join(app.getPath('appData'), 'OpenNotebook'));
const development = !app.isPackaged;
const token = randomBytes(32).toString('hex');
const dataDir = process.env.OPENNOTEBOOK_DATA_DIR || path.join(app.getPath('userData'), 'knowledge');
const tr = (key, params) => nativeMessage(dataDir, key, params);

async function freePort() {
  const server = createServer();
  return new Promise((resolve, reject) => {
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
}

async function start() {
  const port = await freePort();
  origin = `http://127.0.0.1:${port}`;
  initializeLocale(dataDir, process.resourcesPath);
  const webDir = development ? path.join(root, 'apps/web/out') : path.join(process.resourcesPath, 'web');
  const binary = development
    ? path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
    : path.join(process.resourcesPath, 'backend', process.platform === 'win32' ? 'open-notebook-api.exe' : 'open-notebook-api');
  const args = development ? [path.join(root, 'apps/api/run.py')] : [];
  args.push('--port', String(port), '--data-dir', dataDir, '--web-dir', webDir);
  fs.mkdirSync(dataDir, { recursive: true });
  const log = fs.openSync(path.join(dataDir, 'backend.log'), 'a');
  backend = spawn(binary, args, {
    env: { ...process.env, OPENNOTEBOOK_SESSION_TOKEN: token, PYTHONUTF8: '1' },
    stdio: ['ignore', log, log], windowsHide: true,
  });
  fs.closeSync(log);
  let spawnError;
  backend.on('error', error => { spawnError = error; });
  backend.on('exit', () => {
    if (!quitting && window) {
      dialog.showErrorBox('Racall', tr('native.stopped', { path: path.join(dataDir, 'backend.log') }));
      app.quit();
    }
  });
  let ready = false;
  for (let attempt = 0; attempt < 180; attempt++) {
    if (spawnError) throw spawnError;
    if (backend.exitCode !== null) throw new Error(tr('native.failed', { path: path.join(dataDir, 'backend.log') }));
    try {
      const response = await fetch(origin + '/api/settings', {
        headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(1500),
      });
      if (response.ok) { ready = true; break; }
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 300));
  }
  if (!ready) throw new Error(tr('native.timeout'));
  const uiOrigin = process.env.OPENNOTEBOOK_DEV_URL || origin;
  const partition = session.fromPartition('persist:open-notebook');
  partition.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  partition.webRequest.onBeforeSendHeaders({ urls: [origin + '/*'] }, (details, callback) => {
    details.requestHeaders.Authorization = `Bearer ${token}`;
    callback({ requestHeaders: details.requestHeaders });
  });
  partition.webRequest.onHeadersReceived((details, callback) => {
    const headers = { ...details.responseHeaders };
    if (!process.env.OPENNOTEBOOK_DEV_URL) headers['Content-Security-Policy'] = [
      `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-src blob: 'self'; object-src 'none'; base-uri 'none'; form-action 'none'`,
    ];
    callback({ responseHeaders: headers });
  });
  window = new BrowserWindow({
    width: 1440, height: 940, minWidth: 1000, minHeight: 680, show: process.env.OPENNOTEBOOK_SMOKE_MODE !== '1',
    title: 'Racall', backgroundColor: '#ffffff', autoHideMenuBar: true,
    webPreferences: { preload: path.join(__dirname, 'preload.cjs'), session: partition,
      contextIsolation: true, nodeIntegration: false, sandbox: true, webSecurity: true },
  });
  const trusted = event => {
    if (!window || event.sender !== window.webContents || !event.senderFrame?.url.startsWith(uiOrigin + '/')) {
      throw new Error('Untrusted sender');
    }
  };
  ipcMain.handle('connection', event => { trusted(event); return { origin }; });
  ipcMain.handle('open-vault', event => { trusted(event); return shell.openPath(path.join(dataDir, 'notebooks')); });
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
  window.webContents.on('will-navigate', (event, url) => {
    if (new URL(url).origin !== uiOrigin) event.preventDefault();
  });
  await window.loadURL(uiOrigin);
}

if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => { if (window) { window.restore(); window.focus(); } });
  app.whenReady().then(start).catch(error => { dialog.showErrorBox(tr('native.startTitle'), error.message); app.quit(); });
}
app.on('window-all-closed', () => app.quit());
app.on('before-quit', () => { quitting = true; backend?.kill(); });
