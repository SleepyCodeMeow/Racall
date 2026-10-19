/**
 * Real Electron + frozen API verification using an isolated, synthetic provider.
 * This script never contacts Ollama, a cloud service, or the user's keychain.
 * Run sequentially with the other desktop checks (Electron has a single-instance lock).
 */
const { _electron: electron, expect } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const run = path.join(root, 'test-results', 'workbench-desktop-' + Date.now());
const dataDir = path.join(run, 'data');
const executable = process.env.OPENNOTEBOOK_TEST_EXE;
const en = JSON.parse(fs.readFileSync(path.join(root, 'apps/shared/locales/en.json'), 'utf8'));
const ru = JSON.parse(fs.readFileSync(path.join(root, 'apps/shared/locales/ru.json'), 'utf8'));
fs.mkdirSync(dataDir, { recursive: true });

let app;
let locale = 'en';
let failCatalog = false;
const errors = [];
const checks = [];
const contrast = [];
const observed = { catalogs: 0, pulls: [], cancelledStreams: 0, inference: 0, unexpected: [], settingsWrites: 0, chatRequests: [], catalogProviders: [], firstOpenProviders: [] };
const sockets = new Set();
const activeResponses = new Set();
const installed = new Set(['fixture-local:1', 'fixture-local:2', 'fixture-' + 'long-model-name-'.repeat(10) + ':1']);
const text = key => (locale === 'ru' ? ru : en)[key];

function json(response, status, value) {
  response.writeHead(status, { 'Content-Type': 'application/json' });
  response.end(JSON.stringify(value));
}

const provider = http.createServer(async (request, response) => {
  try {
    const url = new URL(request.url, 'http://127.0.0.1');
    if (request.headers.authorization || request.headers['x-api-key']) {
      observed.unexpected.push('Credential header sent to synthetic provider');
      return json(response, 400, { error: 'Unexpected credential header' });
    }
    if (request.method === 'GET' && url.pathname === '/api/tags') {
      observed.catalogs++;
      if (failCatalog) return json(response, 503, { error: 'Synthetic catalog outage' });
      return json(response, 200, { models: [
        ...Array.from(installed, model => ({ name: model, model, size: 4096 })),
        { name: 'fixture-remote:cloud', model: 'fixture-remote:cloud', size: 0, remote_host: 'https://example.invalid' },
        { name: 'fixture-remote-alias', model: 'fixture-remote-alias', size: 0, remote_host: 'https://example.invalid' },
      ] });
    }
    if (request.method === 'GET' && url.pathname === '/v1/models') {
      observed.catalogs++;
      return json(response, 200, { object: 'list', data: [{ id: 'fixture-server:1', object: 'model' }] });
    }
    if (request.method === 'POST' && url.pathname === '/api/pull') {
      let body = '';
      for await (const chunk of request) {
        body += chunk;
        if (body.length > 1024) throw new Error('Unexpected pull body size');
      }
      const payload = JSON.parse(body);
      assert.deepEqual(Object.keys(payload).sort(), ['model', 'stream']);
      assert.equal(payload.stream, true);
      assert.ok(['fixture-cancel:1', 'fixture-success:1', 'fixture-restart:1'].includes(payload.model));
      observed.pulls.push(payload.model);
      response.writeHead(200, { 'Content-Type': 'application/x-ndjson', 'Cache-Control': 'no-store' });
      activeResponses.add(response);
      response.write(JSON.stringify({ status: 'pulling manifest' }) + '\n');
      let tick = 0;
      let finished = false;
      const timer = setInterval(() => {
        tick++;
        if (payload.model === 'fixture-success:1' && tick >= 5) {
          installed.add(payload.model);
          response.write(JSON.stringify({ status: 'writing manifest' }) + '\n');
          response.write(JSON.stringify({ status: 'success' }) + '\n');
          finished = true;
          response.end();
          clearInterval(timer);
        } else {
          response.write(JSON.stringify({ status: 'pulling fixture-layer', digest: 'sha256:fixture', completed: Math.min(tick, 3) * 1024, total: 4096 }) + '\n');
        }
      }, 650);
      response.on('close', () => {
        clearInterval(timer);
        activeResponses.delete(response);
        if (!finished) observed.cancelledStreams++;
      });
      return;
    }
    if (/chat|completions|generate|embed/i.test(url.pathname)) observed.inference++;
    observed.unexpected.push(request.method + ' ' + url.pathname);
    return json(response, 400, { error: 'Only synthetic catalog and pull operations are supported' });
  } catch (error) {
    observed.unexpected.push(error.message);
    if (!response.headersSent) json(response, 500, { error: 'Synthetic provider assertion failed' });
    else response.end();
  }
});
provider.on('connection', socket => { sockets.add(socket); socket.on('close', () => sockets.delete(socket)); });

async function api(page, endpoint, method = 'GET', body) {
  return page.evaluate(async ({ endpoint, method, body }) => {
    const { origin } = await window.desktop.connection();
    const response = await fetch(origin + '/api' + endpoint, {
      method, headers: { 'Content-Type': 'application/json' },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    if (!response.ok) throw new Error('Smoke API ' + endpoint + ' returned HTTP ' + response.status);
    return response.json();
  }, { endpoint, method, body });
}

async function launch() {
  const env = { ...process.env, OPENNOTEBOOK_DATA_DIR: dataDir, OPENNOTEBOOK_SMOKE_MODE: '1', PYTHON_KEYRING_BACKEND: 'keyring.backends.null.Keyring' };
  for (const key of ['ELECTRON_RUN_AS_NODE', 'OPENNOTEBOOK_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'OLLAMA_API_KEY']) delete env[key];
  app = await electron.launch({ ...(executable ? { executablePath: executable, args: ['--disable-gpu'] } : { args: [root, '--disable-gpu'] }), env, timeout: 60000 });
  const page = await app.firstWindow({ timeout: 60000 });
  page.on('pageerror', error => errors.push(error.message));
  // Electron 44 exposes async ClipboardItem APIs. Materialize every available
  // representation in main-process memory, including images/HTML/RTF/files. No
  // original clipboard content crosses into the renderer, logs, or result files.
  await app.evaluate(async ({ clipboard, ClipboardItem }) => {
    const entries = await clipboard.read();
    // An empty Windows clipboard can be represented by an item with no MIME
    // types. It has no payload to materialize; ClipboardItem({}) is invalid.
    globalThis.__racallWorkbenchClipboardSnapshot = await Promise.all(entries.filter(item => item.types.length > 0).map(async item => {
      const values = await Promise.all(item.types.map(async type => {
        const payload = await item.getType(type);
        return [type, type === 'electron application/bookmark' ? payload : new Blob([await payload.arrayBuffer()], { type: payload.type })];
      }));
      return new ClipboardItem(Object.fromEntries(values));
    }));
  });
  const origin = new URL(page.url()).origin;
  await page.route('**/*', async route => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin !== origin && !['data:', 'blob:'].includes(url.protocol)) {
      errors.push('Unexpected renderer network origin: ' + url.origin);
      return route.abort();
    }
    if (url.pathname === '/api/settings' && request.method() === 'PUT') {
      const body = request.postDataJSON();
      if ('api_key' in body || 'embedding_api_key' in body) {
        errors.push('Workbench smoke attempted a keychain write');
        return route.abort();
      }
      observed.settingsWrites++;
    }
    if (url.pathname === '/api/models' && request.method() === 'GET') observed.catalogProviders.push(url.searchParams.get('provider'));
    if (request.method() === 'POST' && /^\/api\/notebooks\/[^/]+\/chats(?:\/[^/]+\/turns)?$/.test(url.pathname)) {
      // A model-selection submit must never bubble into the surrounding chat
      // composer. Record the regression while preventing any inference if broken.
      observed.chatRequests.push(url.pathname);
      return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Unexpected chat submission blocked by isolated smoke' }) });
    }
    await route.continue();
  });
  await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].webContents.setBackgroundThrottling(false));
  await page.locator('.navigation').waitFor();
  await page.locator('.notebook-list .skeleton').waitFor({ state: 'hidden' });
  locale = await page.locator('html').getAttribute('lang');
  return page;
}

async function close() {
  if (!app) return;
  const previous = app;
  app = undefined;
  try {
    await previous.evaluate(async ({ clipboard }) => {
      const saved = globalThis.__racallWorkbenchClipboardSnapshot;
      const owned = globalThis.__racallWorkbenchClipboardOwnedText;
      // Do not overwrite a newer clipboard copy made by the user during testing.
      if (saved && owned && await clipboard.readText() === owned) {
        if (saved.length) await clipboard.write(saved);
        else clipboard.clear();
      }
      delete globalThis.__racallWorkbenchClipboardSnapshot;
      delete globalThis.__racallWorkbenchClipboardOwnedText;
    }).catch(() => { throw new Error('Could not restore the clipboard after the isolated UI smoke'); });
  } finally {
    await previous.close();
  }
}

async function assertClipboard(command) {
  const matches = await app.evaluate(async ({ clipboard }, command) => {
    if (await clipboard.readText() !== command) return false;
    globalThis.__racallWorkbenchClipboardOwnedText = command;
    return true;
  }, command);
  assert.ok(matches, 'The clipboard did not contain the fixed launch command');
}

async function checkClipboardFailure(page) {
  await app.evaluate(({ clipboard }) => {
    globalThis.__racallWorkbenchWriteText = clipboard.writeText;
    clipboard.writeText = () => { throw new Error('Synthetic clipboard denial'); };
  });
  try {
    await page.getByRole('button', { name: /Codex CLI/ }).click();
    const command = page.locator('.launch-command-fallback input');
    await expect(command).toHaveValue('ollama launch codex', { timeout: 4000 });
    await expect(command).toHaveAttribute('readonly', '');
    await expect(page.locator('.launch-toast')).toHaveCount(0);
    await command.focus();
    await command.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A');
    assert.equal(await command.evaluate(element => element.selectionEnd - element.selectionStart), 'ollama launch codex'.length);
    await capture(page, `apps-clipboard-error-${locale}.png`);
    await checkLayout(page, 'clipboard failure ' + locale, ['.launch-command-fallback input']);
  } finally {
    await app.evaluate(({ clipboard }) => {
      clipboard.writeText = globalThis.__racallWorkbenchWriteText;
      delete globalThis.__racallWorkbenchWriteText;
    });
  }
}

async function resize(page, width, height) {
  const expected = await app.evaluate(({ BrowserWindow }, { width, height }) => {
    const window = BrowserWindow.getAllWindows()[0];
    window.setSize(width, height);
    const content = window.getContentBounds();
    return { width: content.width, height: content.height };
  }, { width, height });
  // setSize resolves in main before Chromium receives its resize notification.
  await expect.poll(() => page.evaluate(() => ({ width: innerWidth, height: innerHeight }))).toEqual(expected);
}

async function capture(page, filename) {
  await page.evaluate(() => document.fonts.ready);
  // Hidden Electron windows may return the preceding compositor frame. Warm the
  // actual webContents capture before retaining the third frame; no image edits.
  let encoded;
  for (let index = 0; index < 3; index++) {
    encoded = await app.evaluate(async ({ BrowserWindow }) => (await BrowserWindow.getAllWindows()[0].webContents.capturePage(undefined, { stayHidden: true, stayAwake: true })).toPNG().toString('base64'));
    if (index < 2) await new Promise(resolve => setTimeout(resolve, 150));
  }
  fs.writeFileSync(path.join(run, filename), Buffer.from(encoded, 'base64'));
}

async function checkLayout(page, label, selectors) {
  const result = await page.evaluate(({ selectors }) => {
    const bounds = element => {
      const box = element.getBoundingClientRect();
      let top = Math.max(0, box.top), bottom = Math.min(innerHeight, box.bottom);
      let left = Math.max(0, box.left), right = Math.min(innerWidth, box.right);
      for (let parent = element.parentElement; parent; parent = parent.parentElement) {
        const style = getComputedStyle(parent), clip = parent.getBoundingClientRect();
        if (/(auto|scroll|hidden|clip)/.test(style.overflowY)) {
          top = Math.max(top, clip.top + parent.clientTop);
          bottom = Math.min(bottom, clip.top + parent.clientTop + parent.clientHeight);
        }
        if (/(auto|scroll|hidden|clip)/.test(style.overflowX)) {
          left = Math.max(left, clip.left + parent.clientLeft);
          right = Math.min(right, clip.left + parent.clientLeft + parent.clientWidth);
        }
      }
      return { left: box.left, top: box.top, right: box.right, bottom: box.bottom, width: box.width, height: box.height, visibleHeight: Math.max(0, bottom - top), visibleWidth: Math.max(0, right - left) };
    };
    const rgb = value => {
      const components = value.match(/[\d.]+/g)?.map(Number) ?? [];
      return components.length >= 3 ? [components[0], components[1], components[2], components[3] ?? 1] : [0, 0, 0, 0];
    };
    const luminance = color => color.slice(0, 3).map(value => {
      const normalized = value / 255;
      return normalized <= .04045 ? normalized / 12.92 : ((normalized + .055) / 1.055) ** 2.4;
    }).reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0);
    const values = [];
    for (const selector of selectors) {
      const element = document.querySelector(selector);
      if (!element || !element.checkVisibility()) continue;
      const style = getComputedStyle(element);
      let parent = element;
      let background;
      while (parent && !background) {
        const candidate = rgb(getComputedStyle(parent).backgroundColor);
        if (candidate[3] === 1) background = candidate;
        parent = parent.parentElement;
      }
      const foreground = rgb(style.color);
      if (!background || foreground[3] !== 1) throw new Error('Expected opaque contrast sample: ' + selector);
      const levels = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
      const large = parseFloat(style.fontSize) >= 24 || (parseFloat(style.fontSize) >= 18.66 && parseInt(style.fontWeight) >= 700);
      values.push({ selector, ratio: (levels[0] + .05) / (levels[1] + .05), minimum: large ? 3 : 4.5, color: style.color, background, bounds: bounds(element) });
    }
    return { viewport: { width: innerWidth, height: innerHeight }, scrollWidth: document.documentElement.scrollWidth, samples: values };
  }, { selectors });
  contrast.push({ label, ...result });
  assert.ok(result.scrollWidth <= result.viewport.width + 1, label + ': document overflows horizontally');
  assert.ok(result.samples.length > 0, label + ': no visible contrast samples');
  for (const sample of result.samples) {
    assert.ok(sample.ratio >= sample.minimum - .02, `${label}: ${sample.selector} contrast ${sample.ratio.toFixed(2)} < ${sample.minimum}`);
    assert.ok(sample.bounds.left >= -1 && sample.bounds.right <= result.viewport.width + 1, label + ': control outside horizontal viewport: ' + sample.selector);
    assert.ok(sample.bounds.top >= -1 && sample.bounds.bottom <= result.viewport.height + 1, label + ': control outside vertical viewport: ' + sample.selector);
    assert.ok(sample.bounds.visibleHeight + 1 >= sample.bounds.height && sample.bounds.visibleWidth + 1 >= sample.bounds.width, label + ': control clipped by ancestor overflow: ' + sample.selector);
  }
}

async function settings(page) {
  await page.locator('.nav-bottom > button').click();
  await page.locator('#interface-language').waitFor();
}

async function setTheme(page, theme) {
  const label = page.locator('.theme-choice').filter({ has: page.locator(`input[value="${theme}"]`) });
  await label.click();
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', theme);
  await expect.poll(async () => (await api(page, '/appearance')).theme).toBe(theme);
  await expect.poll(() => app.evaluate(({ nativeTheme }) => nativeTheme.themeSource)).toBe(theme);
}

async function apps(page) {
  await page.locator('.global-nav button').click();
  await expect(page.locator('.apps-page h1')).toHaveText(text('apps.title'));
}

async function chat(page) {
  await page.getByRole('tab', { name: text('nav.chat'), exact: true }).click();
  await page.locator('.composer .model-picker-trigger').waitFor();
}

async function picker(page) {
  await page.locator('.composer .model-picker-trigger').click();
  const dialog = page.getByRole('dialog', { name: text('models.title'), exact: true });
  await dialog.waitFor();
  return dialog;
}

async function startDownload(page, dialog, model) {
  await dialog.locator('.model-manual summary').click();
  await dialog.getByLabel(text('models.modelId'), { exact: true }).fill(model);
  const count = observed.pulls.length;
  await dialog.getByRole('button', { name: text('models.download'), exact: true }).click();
  await expect(dialog.locator('.model-download-confirm')).toContainText(model);
  assert.equal(observed.pulls.length, count, 'Opening the confirmation must not download');
  await dialog.getByRole('button', { name: text('models.confirmDownload'), exact: true }).click();
  await expect.poll(() => observed.pulls.length).toBe(count + 1);
  await expect(dialog.getByRole('progressbar', { name: text('models.layerProgress'), exact: true })).toBeVisible({ timeout: 10000 });
  assert.equal(await dialog.locator('progress').getAttribute('max'), '4096');
  await expect(dialog.locator('.model-download-status small')).toContainText('KB');
}

async function main() {
  await new Promise(resolve => provider.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${provider.address().port}/v1`;
  const profiles = Object.fromEntries(['openai', 'anthropic', 'ollama', 'ollama_cloud', 'llama_cpp', 'openai_compatible'].map(id => [id, { base_url: base, model: id === 'ollama' ? 'fixture-local:1' : 'saved-' + id }]));
  const embeddings = { provider: 'llama_cpp', base_url: base, model: 'independent-embedding-fixture' };
  fs.writeFileSync(path.join(dataDir, 'settings.json'), JSON.stringify({ provider: 'ollama', profiles, embeddings }));
  let page = await launch();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await expect(page.getByRole('heading', { name: en['welcome.title'], exact: true })).toBeVisible();
  checks.push('fresh profile defaults to light and preserves onboarding');

  await apps(page);
  assert.equal(await page.locator('.launcher-button').count(), 8);
  assert.equal(observed.catalogs, 0, 'Apps navigation must not contact model providers');
  assert.equal(observed.pulls.length, 0);
  await capture(page, 'apps-light-en.png');
  await checkLayout(page, 'apps light', ['.apps-page h1', '.apps-content h2', '.apps-description', '.launcher-button > span:not(.launcher-mark)']);
  checks.push('Apps navigation does not contact model providers or start downloads');

  await page.locator('.new-notebook').click();
  await page.getByLabel(en['notebook.name'], { exact: true }).fill('Workbench fixture');
  await page.getByRole('button', { name: en['notebook.create'], exact: true }).click();
  await expect(page.locator('.workspace-header h1')).toHaveText('Workbench fixture');
  await expect(page.locator('.composer textarea')).toBeDisabled();
  const initialSettings = await api(page, '/settings');
  const notebook = (await api(page, '/notebooks')).find(item => item.title === 'Workbench fixture');
  // Create one genuine ready source without performing embeddings. The independent
  // embedding profile is restored before any model-selection assertions.
  await api(page, '/settings', 'PUT', { provider: 'ollama', embeddings: { ...embeddings, model: '' } });
  await page.locator('.source-toggle').click();
  await page.locator('input[type="file"]').setInputFiles({ name: 'Workbench fixture.md', mimeType: 'text/markdown', buffer: Buffer.from('# Workbench fixture\n\nThis local document is only used to enable the real source-grounded composer.\n') });
  await expect.poll(async () => (await api(page, `/notebooks/${notebook.id}/sources`))[0]?.status, { timeout: 30000 }).toBe('ready');
  await api(page, '/settings', 'PUT', { provider: 'ollama', embeddings });
  await page.locator('.source-toggle').click();
  await expect(page.locator('.composer textarea')).toBeEnabled();
  const draft = 'Keep this unsent draft when choosing a model.';
  await page.locator('.composer textarea').fill(draft);
  let dialog = await picker(page);
  await expect(dialog.locator('.model-option').filter({ hasText: 'fixture-local:1' })).toBeVisible();
  observed.firstOpenProviders = [...observed.catalogProviders];
  await dialog.locator('.model-manual summary').click();
  await dialog.getByLabel(en['models.modelId'], { exact: true }).fill('fixture-local:1');
  await dialog.getByRole('button', { name: en['models.use'], exact: true }).click();
  await expect(dialog).toBeHidden();
  await page.waitForTimeout(300);
  assert.deepEqual(observed.chatRequests, [], 'Manual model selection must not submit a chat or create a thread');
  await expect(page.locator('.composer textarea')).toHaveValue(draft);
  dialog = await picker(page);
  await dialog.locator('.model-manual summary').click();
  await dialog.getByLabel(en['models.modelId'], { exact: true }).fill('fixture-local:1');
  await dialog.getByLabel(en['models.modelId'], { exact: true }).press('Enter');
  await expect(dialog).toBeHidden();
  await page.waitForTimeout(300);
  assert.deepEqual(observed.chatRequests, [], 'Pressing Enter in the model ID must not submit the surrounding composer');
  await expect(page.locator('.composer textarea')).toHaveValue(draft);
  dialog = await picker(page);
  await dialog.getByLabel(en['models.search'], { exact: true }).fill('fixture-local:1');
  await dialog.getByLabel(en['models.search'], { exact: true }).press('Enter');
  await page.waitForTimeout(300);
  assert.deepEqual(observed.chatRequests, [], 'Pressing Enter in model search must not submit the surrounding composer');
  await expect(page.locator('.composer textarea')).toHaveValue(draft);
  await page.keyboard.press('Escape');
  await page.locator('.composer textarea').fill('');
  checks.push('manual model button, model ID Enter, and search Enter preserve unsent draft and never create chats or turns');

  await apps(page);
  const launchers = await page.locator('.launcher-button').evaluateAll(buttons => buttons.map(button => ({ command: button.title, name: button.innerText })));
  const catalogCount = observed.catalogs;
  for (let index = 0; index < launchers.length; index++) {
    const command = launchers[index].command;
    assert.match(command, /^ollama launch (claude|codex|opencode|cline|copilot|qwen|droid|pi)$/);
    await page.locator('.launcher-button').nth(index).click();
    await expect(page.locator('.launch-toast')).toContainText(en['apps.copied']);
    await assertClipboard(command);
    if (index === 0) await capture(page, 'apps-toast-light-en.png');
  }
  const previousClipboard = await app.evaluate(({ clipboard }) => clipboard.readText());
  await assert.rejects(() => page.evaluate(async () => window.desktop.copyLaunchCommand('claude; echo injected')), /Unknown launch integration/);
  assert.ok(await app.evaluate(({ clipboard }) => clipboard.readText()) === previousClipboard, 'Invalid launcher input must leave the clipboard untouched');
  await checkClipboardFailure(page);
  await page.getByRole('button', { name: /Codex CLI/ }).click();
  await expect(page.locator('.launch-command-fallback')).toHaveCount(0);
  await expect(page.locator('.launch-toast')).toContainText(en['apps.copied']);
  await assertClipboard('ollama launch codex');
  await page.locator('.launch-toast .icon-button').click();
  assert.equal(observed.catalogs, catalogCount);
  assert.equal(observed.pulls.length, 0);
  checks.push('all eight Apps buttons copy fixed commands with toast and no inference or downloads');
  checks.push('clipboard failure exposes a keyboard-selectable command, clears stale success, and recovers on the next copy');
  await chat(page);
  dialog = await picker(page);
  await expect(dialog.locator('.model-option').filter({ hasText: 'fixture-local:2' })).toBeVisible();
  await expect(dialog.locator('.model-option').filter({ hasText: 'fixture-remote:cloud' })).toContainText(en['models.cloud']);
  assert.equal(observed.pulls.length, 0);
  await dialog.getByLabel(en['models.search'], { exact: true }).fill('FIXTURE-LOCAL:2');
  await expect(dialog.locator('.model-option')).toHaveCount(1);
  await dialog.getByLabel(en['models.search'], { exact: true }).press('ArrowDown');
  await expect(dialog.locator('.model-option')).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(dialog).toBeHidden();
  await expect(page.locator('.model-picker-trigger')).toContainText('fixture-local:2');
  const selected = await api(page, '/settings');
  assert.deepEqual(selected.embeddings, initialSettings.embeddings);
  for (const [id, profile] of Object.entries(initialSettings.profiles)) if (id !== 'ollama') assert.deepEqual(selected.profiles[id], profile);
  assert.equal(observed.pulls.length, 0);
  checks.push('search and keyboard selection persist the real saved model without changing embeddings or other profiles');

  dialog = await picker(page);
  await dialog.locator('.model-option').filter({ hasText: 'fixture-remote:cloud' }).click();
  await expect(dialog).toBeHidden();
  await expect(page.locator('.model-picker-trigger').getByRole('img', { name: en['models.cloud'], exact: true })).toBeVisible();
  assert.equal(observed.pulls.length, 0, 'Selecting an Ollama cloud model must not download weights');
  dialog = await picker(page);
  await dialog.locator('.model-option').filter({ hasText: 'fixture-remote-alias' }).click();
  await expect(dialog).toBeHidden();
  await expect(page.locator('.model-picker-trigger').getByRole('img', { name: en['models.cloud'], exact: true })).toBeVisible();
  const catalogsBeforeRestart = observed.catalogs;
  await close();
  page = await launch();
  await expect(page.locator('.model-picker-trigger')).toContainText('fixture-remote-alias');
  await expect(page.locator('.model-picker-trigger').getByRole('img', { name: en['models.local'], exact: true })).toHaveCount(0);
  assert.equal(observed.catalogs, catalogsBeforeRestart, 'Restoring a selection must not eagerly discover models');
  dialog = await picker(page);
  await expect(dialog.locator('.model-option').filter({ hasText: 'fixture-remote-alias' })).toBeVisible();
  await dialog.locator('.model-provider-select').selectOption('llama_cpp');
  await expect(dialog.locator('.model-option')).toContainText('fixture-server:1');
  await expect(page.locator('.model-picker-trigger').getByRole('img', { name: en['models.cloud'], exact: true })).toBeVisible();
  await page.keyboard.press('Escape');
  dialog = await picker(page);
  await dialog.locator('.model-option').filter({ hasText: 'fixture-local:2' }).click();
  await expect(dialog).toBeHidden();
  await expect(page.locator('.model-picker-trigger').getByRole('img', { name: en['models.local'], exact: true })).toBeVisible();
  checks.push('Ollama cloud and local selections expose the correct model type without inference or downloads');

  dialog = await picker(page);
  await dialog.locator('.model-provider-select').selectOption('llama_cpp');
  await expect(dialog.locator('.model-option')).toContainText('fixture-server:1');
  await expect(dialog.locator('.model-option')).toContainText(en['models.server']);
  await expect(dialog.locator('.model-option').getByRole('img', { name: en['models.server'], exact: true })).toBeVisible();
  await expect(dialog.locator('.model-download-button')).toHaveCount(0);
  await dialog.locator('.model-option').click();
  await expect(dialog).toBeHidden();
  await expect.poll(async () => (await api(page, '/settings')).provider).toBe('llama_cpp');
  await expect(page.locator('.model-picker-trigger').getByRole('img', { name: en['models.server'], exact: true })).toBeVisible();
  dialog = await picker(page);
  await dialog.locator('.model-provider-select').selectOption('ollama');
  await dialog.locator('.model-option').filter({ hasText: 'fixture-local:2' }).click();
  await expect(dialog).toBeHidden();
  await expect(page.locator('.model-picker-trigger')).toContainText('fixture-local:2');
  await capture(page, 'chat-light-en.png');
  await checkLayout(page, 'chat light', ['.workspace-header h1', '.chat-welcome h2', '.model-picker-trigger']);

  dialog = await picker(page);
  await dialog.locator('.model-provider-select').selectOption('ollama_cloud');
  await expect(dialog.getByRole('alert')).toContainText(en['error.models.1']);
  await expect(dialog.locator('.model-download-button')).toHaveCount(0);
  await dialog.locator('.model-provider-select').selectOption('ollama');
  await expect(dialog.locator('.model-option').filter({ hasText: 'fixture-local:2' })).toBeVisible();
  await dialog.locator('.model-manual summary').click();
  await dialog.getByLabel(en['models.modelId'], { exact: true }).fill('fixture-remote:cloud');
  await expect(dialog.getByRole('button', { name: en['models.download'], exact: true })).toBeDisabled();
  assert.equal(observed.pulls.length, 0);
  await page.keyboard.press('Escape');
  await expect(page.locator('.model-picker-trigger')).toBeFocused();
  checks.push('server and cloud modes stay distinct; cloud requires credentials and never offers weight download');

  dialog = await picker(page);
  failCatalog = true;
  await dialog.getByRole('button', { name: en['models.refresh'], exact: true }).click();
  await expect(dialog.getByRole('alert')).toContainText('503');
  await expect(dialog.locator('.model-option')).toHaveCount(0);
  failCatalog = false;
  await dialog.getByRole('button', { name: en['models.refresh'], exact: true }).click();
  await expect(dialog.locator('.model-option').filter({ hasText: 'fixture-local:2' })).toBeVisible();
  checks.push('failed provider discovery displays an error and refresh recovers');

  await startDownload(page, dialog, 'fixture-cancel:1');
  await dialog.getByRole('button', { name: en['models.cancelDownload'], exact: true }).click();
  await expect(dialog.locator('.model-download-status')).toContainText(en['models.phaseCancelled']);
  await expect.poll(() => observed.cancelledStreams).toBe(1);
  assert.equal((await api(page, '/models/downloads')).job.status, 'cancelled');
  // The manual section remains expanded after confirmation.
  await dialog.locator('.model-manual summary').click();
  await startDownload(page, dialog, 'fixture-success:1');
  await expect(dialog.locator('.model-download-status')).toContainText(en['models.phaseCompleted'], { timeout: 10000 });
  await expect(dialog.locator('.model-option').filter({ hasText: 'fixture-success:1' })).toBeVisible();
  assert.equal((await api(page, '/settings')).profiles.ollama.model, 'fixture-local:2', 'Downloading must not automatically select the model');
  assert.deepEqual((await api(page, '/settings')).embeddings, initialSettings.embeddings);
  await page.keyboard.press('Escape');
  checks.push('explicit confirmed synthetic download shows byte progress, cancels its request, and refreshes on success without auto-selection');

  await settings(page);
  await setTheme(page, 'dark');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.locator('#interface-language').selectOption('ru');
  locale = 'ru';
  await expect(page.locator('.settings h1')).toHaveText(ru['settings.title']);
  await expect(page.locator('.theme-choice')).toContainText([ru['settings.themeLight'], ru['settings.themeDark'], ru['settings.themeSystem']]);
  await page.locator('.settings').evaluate(element => { element.scrollTop = 0; });
  await capture(page, 'settings-dark-ru.png');
  await apps(page);
  await page.getByRole('button', { name: /Codex CLI/ }).click();
  await expect(page.locator('.launch-toast')).toContainText(ru['apps.paste']);
  await assertClipboard('ollama launch codex');
  await checkClipboardFailure(page);
  await page.getByRole('button', { name: /Codex CLI/ }).click();
  await expect(page.locator('.launch-command-fallback')).toHaveCount(0);
  await page.locator('.launch-toast .icon-button').click();
  await capture(page, 'apps-dark-ru.png');
  await checkLayout(page, 'apps dark Russian', ['.apps-page h1', '.apps-content h2', '.apps-description', '.launcher-button > span:not(.launcher-mark)']);
  await chat(page);
  await capture(page, 'chat-dark-ru.png');
  await checkLayout(page, 'chat dark Russian', ['.workspace-header h1', '.chat-welcome h2', '.model-picker-trigger']);
  dialog = await picker(page);
  await expect(dialog.getByLabel(ru['models.search'], { exact: true })).toBeVisible();
  await expect(dialog.locator('.model-picker-list')).toHaveAttribute('aria-busy', 'false');
  await expect(dialog.locator('.model-option').filter({ hasText: 'fixture-local:2' })).toBeVisible();
  await dialog.evaluate(element => { element.scrollTop = 0; });
  await capture(page, 'models-dark-ru.png');
  await page.keyboard.press('Escape');
  checks.push('Apps, themes, and model picker translate live between English and Russian');

  // Visit the existing workspace surfaces in dark mode without starting research
  // or changing notes. Their ordinary data reads are local to the fresh profile.
  for (const key of ['nav.notes', 'nav.research', 'nav.artifacts']) {
    await page.getByRole('tab', { name: text(key), exact: true }).click();
    await checkLayout(page, 'dark ' + key, ['.workspace-header h1']);
  }
  await page.getByRole('button', { name: text('nav.connect'), exact: true }).click();
  await expect(page.locator('.config-block')).toContainText('mcpServers');
  await checkLayout(page, 'dark connections', ['.workspace-header h1']);
  await chat(page);
  await page.locator('.source-toggle').click();
  await expect(page.locator('#source-drawer')).toBeVisible();
  await checkLayout(page, 'dark source drawer', ['.workspace-header h1', '.source-panel .panel-heading']);
  await page.locator('.source-toggle').click();
  checks.push('existing notes, research, reports, MCP connection, and source drawer remain reachable in dark mode');

  await settings(page);
  await page.locator('#interface-language').selectOption('en');
  locale = 'en';
  await expect(page.locator('.settings h1')).toHaveText(en['settings.title']);
  await chat(page);
  await resize(page, 1000, 680);
  observed.minimumNotebook = await page.locator('.notebook-entry > button:first-child').evaluate(element => {
    const box = element.getBoundingClientRect();
    let top = Math.max(0, box.top);
    let bottom = Math.min(innerHeight, box.bottom);
    for (let parent = element.parentElement; parent; parent = parent.parentElement) {
      if (!/(auto|scroll|hidden|clip)/.test(getComputedStyle(parent).overflowY)) continue;
      const clip = parent.getBoundingClientRect();
      top = Math.max(top, clip.top + parent.clientTop);
      bottom = Math.min(bottom, clip.top + parent.clientTop + parent.clientHeight);
    }
    return { height: box.height, visibleHeight: Math.max(0, bottom - top) };
  });
  assert.ok(observed.minimumNotebook.visibleHeight + 1 >= observed.minimumNotebook.height, 'The single notebook row must remain fully visible at minimum desktop size');
  dialog = await picker(page);
  await checkLayout(page, 'minimum desktop model picker', ['.workspace-header h1', '.model-picker-trigger', '.model-picker-popup', '.model-picker-topline h3', '.model-provider-label']);
  await dialog.locator('.model-manual summary').click();
  await dialog.getByLabel(en['models.modelId'], { exact: true }).fill('fixture-viewport:1');
  await dialog.getByRole('button', { name: en['models.download'], exact: true }).click();
  await dialog.getByRole('button', { name: en['models.confirmDownload'], exact: true }).scrollIntoViewIfNeeded();
  await checkLayout(page, 'minimum desktop expanded model confirmation', ['.model-picker-popup', '.model-download-confirm .model-download-button']);
  await capture(page, 'model-picker-minimum-dark-en.png');
  assert.equal(observed.pulls.length, 2, 'Viewport inspection must not confirm a download');
  observed.confirmationFocusTag = await page.evaluate(() => document.activeElement.tagName);
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
  await expect(page.locator('.model-picker-trigger')).toBeFocused();
  await resize(page, 1440, 940);

  dialog = await picker(page);
  await startDownload(page, dialog, 'fixture-restart:1');
  await close();
  await expect.poll(() => activeResponses.size).toBe(0);
  const pullCount = observed.pulls.length;
  page = await launch();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  assert.equal(await app.evaluate(({ nativeTheme }) => nativeTheme.themeSource), 'dark');
  assert.equal(locale, 'en');
  dialog = await picker(page);
  await expect(dialog.locator('.model-download-status')).toContainText(en['models.phaseInterrupted']);
  assert.equal((await api(page, '/models/downloads')).job.status, 'interrupted');
  assert.equal(observed.pulls.length, pullCount, 'A full app restart must not replay a download');
  await page.keyboard.press('Escape');
  checks.push('full restart preserves dark theme and model selection; interrupted download is recovered without replay');

  await settings(page);
  await page.emulateMedia({ colorScheme: 'dark' });
  await setTheme(page, 'system');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.emulateMedia({ colorScheme: 'light' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.emulateMedia({ colorScheme: 'dark' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await close();
  page = await launch();
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'system');
  const system = await page.evaluate(() => ({ expected: matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light', actual: document.documentElement.dataset.theme }));
  assert.equal(system.actual, system.expected);
  assert.equal(await app.evaluate(({ nativeTheme }) => nativeTheme.themeSource), 'system');
  checks.push('system theme follows live media changes and persists across a full app restart with native title bar source');

  await settings(page);
  await setTheme(page, 'light');
  await close();
  page = await launch();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  assert.equal(await app.evaluate(({ nativeTheme }) => nativeTheme.themeSource), 'light');
  const finalSettings = await api(page, '/settings');
  assert.equal(finalSettings.provider, 'ollama');
  assert.equal(finalSettings.profiles.ollama.model, 'fixture-local:2');
  assert.deepEqual(finalSettings.embeddings, initialSettings.embeddings);
  for (const id of ['openai', 'anthropic', 'ollama_cloud', 'openai_compatible']) assert.deepEqual(finalSettings.profiles[id], initialSettings.profiles[id]);
  assert.equal(observed.pulls.length, 3);
  assert.equal(observed.inference, 0);
  assert.deepEqual(observed.unexpected, []);
  assert.ok(observed.firstOpenProviders.length > 0 && observed.firstOpenProviders.every(id => id === 'ollama'), 'Initial model picker must only request the saved provider');
  assert.deepEqual(errors, []);
  assert.ok(observed.settingsWrites >= 3);
  checks.push('light preference survives restart; zero inference, real-model downloads, credential writes, or external renderer requests');
  await close();
  const result = { passed: true, packaged: Boolean(executable), checks, observations: observed, contrast, errors, artifacts: run };
  fs.writeFileSync(path.join(run, 'result.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
}

main().catch(async error => {
  if (app) {
    const page = app.windows()[0];
    if (page) {
      await capture(page, 'failure.png').catch(() => {});
      fs.writeFileSync(path.join(run, 'failure-body.txt'), await page.locator('body').innerText().catch(() => ''));
    }
  }
  const result = { passed: false, packaged: Boolean(executable), error: error.message, checks, observations: observed, contrast, errors, artifacts: run };
  fs.writeFileSync(path.join(run, 'result.json'), JSON.stringify(result, null, 2));
  console.error(error);
  console.error(JSON.stringify(result));
  process.exitCode = 1;
}).finally(async () => {
  await close();
  for (const response of activeResponses) response.destroy();
  for (const socket of sockets) socket.destroy();
  await new Promise(resolve => provider.close(resolve));
});
