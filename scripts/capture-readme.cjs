/** Capture the real static desktop UI with sample documents and presentation-only framing. */
const { chromium, expect } = require('@playwright/test');
const { spawn } = require('node:child_process');
const { randomBytes, createHash } = require('node:crypto');
const { createServer } = require('node:net');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const release = require('../apps/shared/release.json');
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const materials = [
  [
    'Connected notes.md',
    '# Connected notes\n\nA useful note keeps one idea and its context. Links between notes help you return to ideas and discover connections.\n\n## Sources\n\nKeep original documents beside your own conclusions so you can check every citation.',
  ],
  [
    'Research questions.md',
    '# Research questions\n\nWhich ideas appear across several sources? Where do the authors disagree? Which claims need more evidence?',
  ],
  [
    'My knowledge library.md',
    '# My knowledge library\n\nA notebook brings together materials about one topic. Original files stay beside Markdown notes. The search index can be rebuilt without changing the documents.',
  ],
];

(async () => {
  assert.ok(release.version && release.label, 'Release version and label are required.');
  const run = path.join(root, 'test-results', 'readme-capture-' + Date.now());
  fs.mkdirSync(run, { recursive: true });
  const socket = createServer();
  await new Promise((resolve) => socket.listen(0, '127.0.0.1', resolve));
  const port = socket.address().port;
  await new Promise((resolve) => socket.close(resolve));
  const origin = `http://127.0.0.1:${port}`;
  const token = randomBytes(32).toString('hex');
  const providerRequests = [];
  const provider = http.createServer((request, response) => {
    providerRequests.push(request.method + ' ' + request.url);
    response.writeHead(503).end();
  });
  await new Promise((resolve) => provider.listen(0, '127.0.0.1', resolve));
  const endpoint = `http://127.0.0.1:${provider.address().port}/v1`;
  const env = {
    ...process.env,
    OPENNOTEBOOK_SESSION_TOKEN: token,
    PYTHONUTF8: '1',
    PYTHON_KEYRING_BACKEND: 'keyring.backends.null.Keyring',
  };
  for (const key of [
    'OPENNOTEBOOK_API_KEY',
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY',
    'OLLAMA_API_KEY',
  ])
    delete env[key];
  const log = fs.openSync(path.join(run, 'backend.log'), 'a');
  const python = path.join(
    root,
    '.venv',
    process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
  );
  const backend = spawn(
    python,
    [
      'apps/api/run.py',
      '--port',
      String(port),
      '--data-dir',
      path.join(run, 'data'),
      '--web-dir',
      path.join(root, 'apps/web/out'),
    ],
    {
      cwd: root,
      env,
      windowsHide: true,
      stdio: ['ignore', log, log],
    },
  );
  fs.closeSync(log);
  let spawnError, browser;
  backend.on('error', (error) => {
    spawnError = error;
  });
  const api = async (endpoint, method = 'GET', body) => {
    const response = await fetch(origin + '/api' + endpoint, {
      method,
      signal: AbortSignal.timeout(5000),
      headers: {
        Authorization: `Bearer ${token}`,
        ...(body && !(body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
      },
      body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body),
    });
    assert.ok(response.ok, `${endpoint}: HTTP ${response.status}`);
    return response.json();
  };
  try {
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt++) {
      if (spawnError) throw spawnError;
      assert.equal(backend.exitCode, null, 'Backend exited before becoming ready.');
      try {
        await api('/settings');
        ready = true;
        break;
      } catch {
        await delay(200);
      }
    }
    assert.ok(ready, 'Backend startup timed out.');
    await api('/settings', 'PUT', {
      provider: 'openai_compatible',
      profiles: { openai_compatible: { base_url: endpoint, model: '' } },
      embeddings: { provider: 'openai_compatible', base_url: endpoint, model: '' },
    });
    await api('/preferences', 'PUT', { locale: 'en' });
    await api('/appearance', 'PUT', { theme: 'light' });
    const notebook = await api('/notebooks', 'POST', { title: 'Personal knowledge' });
    for (const title of ['Project ideas', 'Books and notes'])
      await api('/notebooks', 'POST', { title });
    for (const [name, text] of materials) {
      const form = new FormData();
      form.append('file', new Blob([text], { type: 'text/markdown' }), name);
      await api(`/notebooks/${notebook.id}/sources`, 'POST', form);
    }
    await expect
      .poll(
        async () =>
          (await api(`/notebooks/${notebook.id}/sources`)).filter((item) => item.status === 'ready')
            .length,
        { timeout: 60000 },
      )
      .toBe(3);
    assert.equal((await api('/settings')).embeddings.model, '');
    const chrome =
      process.env.RACALL_BROWSER_PATH ||
      (process.platform === 'win32'
        ? 'C:/Program Files/Google/Chrome/Application/chrome.exe'
        : undefined);
    browser = await chromium.launch({
      headless: true,
      args: ['--disable-gpu'],
      ...(chrome ? { executablePath: chrome } : {}),
    });
    const page = await browser.newPage({
      viewport: { width: 1408, height: 948 },
      deviceScaleFactor: 1,
    });
    const errors = [],
      externalRequests = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.route('**/*', (route) => {
      const url = new URL(route.request().url());
      if (url.origin === origin || ['data:', 'blob:'].includes(url.protocol))
        return route.continue();
      externalRequests.push(url.origin);
      return route.abort();
    });
    await page.goto(origin + '/#token=' + token);
    await page.getByRole('button', { name: 'Personal knowledge', exact: true }).click();
    await expect(
      page.getByRole('heading', { name: 'What will we explore today?', exact: true }),
    ).toBeVisible();
    await page.getByRole('button', { name: 'Material actions', exact: true }).click();
    await expect(page.locator('.actions-popover')).toBeVisible();
    // Preserve the approved orange presentation artwork, without changing UI text or controls.
    await page.addStyleTag({
      content:
        'body{padding:64px;background:radial-gradient(ellipse at 18% 0%,#ffe7bb 0%,transparent 60%),linear-gradient(130deg,#f1d9bc,#edbc90 55%,#f8e9d5);}.app-shell{width:1280px;height:820px;min-height:820px;border-radius:16px;box-shadow:0 24px 70px #6e421524,0 0 0 1px #ad774317;overflow:hidden;}.navigation{background:#fcfbf9;}',
    });
    await expect(page.getByRole('button', { name: 'Apps', exact: true })).toBeInViewport();
    await expect(page.getByRole('tab', { name: 'Studio', exact: true })).toBeInViewport();
    await expect(page.locator('.version')).toContainText(release.label);
    await expect(page.locator('.version')).toBeInViewport();
    const logos = await page.evaluate(async () => {
      await document.fonts.ready;
      await Promise.all([...document.images].map((image) => image.decode()));
      return [...document.querySelectorAll('.brand img, .chat-welcome img')].map((image) => ({
        source: image.getAttribute('src'),
        width: image.naturalWidth,
        height: image.naturalHeight,
      }));
    });
    assert.equal(logos.length, 2);
    assert.ok(logos.every((image) => image.width > 0 && image.height > 0));
    const frame = await page.locator('.app-shell').boundingBox();
    assert.deepEqual(frame, { x: 64, y: 64, width: 1280, height: 820 });
    assert.equal(await page.title(), 'Racall');
    assert.deepEqual(errors, []);
    assert.deepEqual(externalRequests, []);
    assert.deepEqual(
      providerRequests,
      [],
      'No inference, embedding, model discovery or download is allowed.',
    );
    const screenshot = path.join(root, 'assets/brand/racall-desktop-preview.png');
    await page.screenshot({ path: screenshot, animations: 'disabled' });
    const result = {
      passed: true,
      screenshot,
      version: release.version,
      viewport: page.viewportSize(),
      frame,
      logos,
      notebookCount: (await api('/notebooks')).length,
      sourceCount: materials.length,
      providerRequests,
      externalRequests,
      errors,
      sha256: createHash('sha256').update(fs.readFileSync(screenshot)).digest('hex'),
      checks: [
        'real isolated API and document imports',
        'English chat welcome and material actions',
        'visible Apps, Studio and ' + release.label,
        'decoded real logos',
        'approved presentation framing',
        'no JavaScript errors or model requests',
      ],
    };
    fs.writeFileSync(path.join(run, 'result.json'), JSON.stringify(result, null, 2) + '\n');
    console.log(JSON.stringify({ passed: true, run, screenshot, sha256: result.sha256 }));
  } finally {
    if (browser) await browser.close();
    const stopped = new Promise((resolve) => backend.once('exit', resolve));
    backend.kill();
    await Promise.race([stopped, delay(5000)]);
    await new Promise((resolve) => provider.close(resolve));
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
