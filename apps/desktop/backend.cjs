const { spawn } = require('node:child_process');
const { createServer } = require('node:net');
const path = require('node:path');
const fs = require('node:fs');
const { initializeLocale } = require('./locale.cjs');

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

/** Own only the Python process; the app lifecycle decides when it may be stopped. */
function createBackendService(runtime, { tr, onExit }) {
  let backend;

  async function start() {
    const { root, development, token, dataDir, backendLog } = runtime;
    const port = await freePort();
    const origin = `http://127.0.0.1:${port}`;
    initializeLocale(dataDir, process.resourcesPath);
    const webDir = development
      ? path.join(root, 'apps/web/out')
      : path.join(process.resourcesPath, 'web');
    const binary = development
      ? path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
      : path.join(
          process.resourcesPath,
          'backend',
          process.platform === 'win32' ? 'open-notebook-api.exe' : 'open-notebook-api',
        );
    const args = development ? [path.join(root, 'apps/api/run.py')] : [];
    args.push('--port', String(port), '--data-dir', dataDir, '--web-dir', webDir);
    fs.mkdirSync(dataDir, { recursive: true });
    const log = fs.openSync(backendLog, 'a');
    // The per-launch bearer token is inherited by Python, never exposed in preload.
    backend = spawn(binary, args, {
      env: { ...process.env, OPENNOTEBOOK_SESSION_TOKEN: token, PYTHONUTF8: '1' },
      stdio: ['ignore', log, log],
      windowsHide: true,
    });
    fs.closeSync(log);
    let spawnError;
    backend.on('error', (error) => {
      spawnError = error;
    });
    backend.on('exit', onExit);
    let ready = false;
    for (let attempt = 0; attempt < 180; attempt++) {
      if (spawnError) throw spawnError;
      if (backend.exitCode !== null) throw new Error(tr('native.failed', { path: backendLog }));
      try {
        const response = await fetch(origin + '/api/settings', {
          headers: { Authorization: `Bearer ${token}` },
          signal: AbortSignal.timeout(1500),
        });
        if (response.ok) {
          ready = true;
          break;
        }
      } catch {}
      await new Promise((resolve) => setTimeout(resolve, 300));
    }
    if (!ready) throw new Error(tr('native.timeout'));
    return origin;
  }

  function stop() {
    backend?.kill();
  }

  return { start, stop };
}

module.exports = { createBackendService };
