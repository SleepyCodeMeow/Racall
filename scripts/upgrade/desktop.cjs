const { _electron: electron, expect } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

/** Drive actual installed binaries; never launch the checkout's Electron entry point. */
class InstalledDesktop {
  constructor(executable, profile, run, errors) {
    this.executable = executable;
    this.profile = profile;
    this.run = run;
    this.errors = errors;
  }

  async launch(version) {
    const env = {
      ...process.env,
      OPENNOTEBOOK_SMOKE_MODE: '1',
      PYTHON_KEYRING_BACKEND: 'keyring.backends.null.Keyring',
    };
    for (const key of [
      'ELECTRON_RUN_AS_NODE',
      'OPENNOTEBOOK_DATA_DIR',
      'OPENNOTEBOOK_DEV_URL',
      'OPENNOTEBOOK_API_KEY',
      'OPENAI_API_KEY',
      'ANTHROPIC_API_KEY',
      'OLLAMA_API_KEY',
    ])
      delete env[key];
    this.app = await electron.launch({
      executablePath: this.executable,
      args: ['--disable-gpu'],
      env,
      timeout: 90000,
    });
    this.page = await this.app.firstWindow({ timeout: 90000 });
    this.page.setDefaultTimeout(20000);
    this.page.on('pageerror', (error) => this.errors.push(error.message));
    this.page.on('dialog', async (dialog) => {
      if (dialog.type() !== 'beforeunload') await dialog.dismiss();
    });
    const info = await this.app.evaluate(({ app, BrowserWindow, screen }) => {
      const window = BrowserWindow.getAllWindows()[0];
      window.webContents.setBackgroundThrottling(false);
      const area = screen.getPrimaryDisplay().workAreaSize;
      window.setSize(
        Math.min(1180, Math.max(1000, area.width)),
        Math.min(820, Math.max(680, area.height)),
      );
      window.showInactive();
      return {
        version: app.getVersion(),
        packaged: app.isPackaged,
        profile: app.getPath('userData'),
        executable: process.execPath,
      };
    });
    assert.equal(info.version, version, 'The requested installed version did not launch.');
    assert.equal(info.packaged, true);
    assert.equal(
      path.resolve(info.profile),
      path.resolve(this.profile),
      'Upgrade must use the original default profile.',
    );
    assert.equal(path.resolve(info.executable), path.resolve(this.executable));
    await this.page.locator('.navigation').waitFor();
    this.origin = await this.page.evaluate(async () => (await window.desktop.connection()).origin);
    assert.match(this.origin, /^http:\/\/127\.0\.0\.1:\d+$/);
    return info;
  }

  async request(endpoint, method = 'GET', body) {
    return this.page.evaluate(
      async ({ endpoint, method, body }) => {
        const response = await fetch('/api' + endpoint, {
          method,
          headers: { 'Content-Type': 'application/json' },
          ...(body === undefined ? {} : { body: JSON.stringify(body) }),
        });
        const text = await response.text();
        return { status: response.status, text };
      },
      { endpoint, method, body },
    );
  }

  async api(endpoint, method = 'GET', body) {
    const response = await this.request(endpoint, method, body);
    assert.ok(
      response.status >= 200 && response.status < 300,
      `HTTP ${response.status}: ${response.text}`,
    );
    return JSON.parse(response.text);
  }

  async text(endpoint) {
    const response = await this.request(endpoint);
    assert.equal(response.status, 200, endpoint);
    return response.text;
  }

  async upload(endpoint, text, method = 'POST') {
    return this.page.evaluate(
      async ({ endpoint, text, method }) => {
        const form = new FormData();
        form.append('file', new Blob([text], { type: 'text/markdown' }), 'upgrade-mission.md');
        const response = await fetch('/api' + endpoint, { method, body: form });
        if (!response.ok) throw new Error(`Upload returned HTTP ${response.status}`);
        return response.json();
      },
      { endpoint, text, method },
    );
  }

  async capture(name) {
    if (this.page)
      await this.page.screenshot({
        path: path.join(this.run, name),
        animations: 'disabled',
        timeout: 15000,
      });
  }

  async downloadLegacy(file) {
    await this.app.evaluate(({ BrowserWindow }, filename) => {
      globalThis.__upgradeDownload = 'waiting';
      BrowserWindow.getAllWindows()[0].webContents.session.once('will-download', (_event, item) => {
        item.setSavePath(filename);
        item.once('done', (_done, state) => {
          globalThis.__upgradeDownload = state;
        });
      });
    }, file);
    await this.page.getByTestId('material-export').click();
    await expect
      .poll(() => this.app.evaluate(() => globalThis.__upgradeDownload))
      .toBe('completed');
    return fs.readFileSync(file, 'utf8');
  }

  async close() {
    if (!this.app) return;
    const app = this.app;
    this.app = undefined;
    // No editors are intentionally dirty in this gate; destroy avoids an unattended native dialog.
    await app.evaluate(({ BrowserWindow }) =>
      BrowserWindow.getAllWindows().forEach((window) => window.destroy()),
    );
    await app.close();
    if (this.origin)
      await expect
        .poll(
          async () => {
            try {
              const response = await fetch(this.origin + '/api/settings', {
                signal: AbortSignal.timeout(500),
              });
              await response.body?.cancel();
              return false;
            } catch {
              return true;
            }
          },
          { timeout: 30000 },
        )
        .toBe(true);
  }
}

module.exports = { InstalledDesktop };
