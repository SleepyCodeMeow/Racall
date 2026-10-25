const path = require('node:path');
const { randomBytes } = require('node:crypto');

/** Resolve the desktop profile before Electron acquires locks or creates sessions. */
function createRuntime(app) {
  const root = path.resolve(__dirname, '../..');
  // Branding must not move existing notebooks or provider settings.
  // Isolated test data also needs its own Chromium profile (locks, caches, cookies).
  const smokeProfile =
    process.env.OPENNOTEBOOK_SMOKE_MODE === '1' && process.env.OPENNOTEBOOK_DATA_DIR
      ? path.join(path.resolve(process.env.OPENNOTEBOOK_DATA_DIR), 'electron-profile')
      : undefined;
  app.setPath('userData', smokeProfile || path.join(app.getPath('appData'), 'OpenNotebook'));
  const development = !app.isPackaged;
  const token = randomBytes(32).toString('hex');
  const dataDir =
    process.env.OPENNOTEBOOK_DATA_DIR || path.join(app.getPath('userData'), 'knowledge');
  return { root, development, token, dataDir, backendLog: path.join(dataDir, 'backend.log') };
}

module.exports = { createRuntime };
