/** Context, Studio, library and job recovery in an isolated Electron profile. */
const { _electron: electron, expect } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { studioProvider } = require('./smoke/studio-provider.cjs');

const root = path.resolve(__dirname, '..');
const run = path.join(root, 'test-results', 'studio-desktop-' + Date.now());
const data = path.join(run, 'data');
fs.mkdirSync(data, { recursive: true });
const en = JSON.parse(fs.readFileSync(path.join(root, 'apps/shared/locales/en.json'), 'utf8'));
const ru = JSON.parse(fs.readFileSync(path.join(root, 'apps/shared/locales/ru.json'), 'utf8'));
const provider = studioProvider();
const errors = [];
let app;

async function launch() {
  const env = { ...process.env, OPENNOTEBOOK_DATA_DIR: data, OPENNOTEBOOK_SMOKE_MODE: '1',
    PYTHON_KEYRING_BACKEND: 'keyring.backends.null.Keyring' };
  for (const key of ['ELECTRON_RUN_AS_NODE', 'OPENNOTEBOOK_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'OLLAMA_API_KEY']) delete env[key];
  app = await electron.launch({
    ...(process.env.OPENNOTEBOOK_TEST_EXE
      ? { executablePath: process.env.OPENNOTEBOOK_TEST_EXE, args: ['--disable-gpu'] }
      : { args: [root, '--disable-gpu'] }), env, timeout: 60000,
  });
  const page = await app.firstWindow({ timeout: 60000 });
  page.setDefaultTimeout(15000);
  page.on('pageerror', error => errors.push(error.message));
  await app.evaluate(({ BrowserWindow, screen }) => {
    const window = BrowserWindow.getAllWindows()[0];
    window.webContents.setBackgroundThrottling(false);
    const hostedCapture = process.env.GITHUB_ACTIONS === 'true' && process.platform !== 'darwin';
    const area = screen.getPrimaryDisplay().workAreaSize;
    window.setSize(hostedCapture ? Math.min(1180, Math.max(1000, area.width)) : 1180,
      hostedCapture ? Math.min(820, Math.max(680, area.height)) : 820);
    // Hidden compositor surfaces can stall CDP screenshots on Windows/Xvfb.
    // Show only this disposable hosted test window; local checks stay hidden.
    if (hostedCapture) window.showInactive();
  });
  await page.locator('.navigation').waitFor();
  assert.equal(await app.evaluate(({ app }) => app.getPath('userData')), path.join(data, 'electron-profile'));
  return page;
}

async function close() {
  if (!app) return;
  const previous = app;
  app = undefined;
  await previous.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().forEach(window => window.destroy())).catch(() => {});
  await previous.close().catch(() => {});
}

async function api(page, endpoint, method = 'GET', body) {
  return page.evaluate(async ({ endpoint, method, body }) => {
    const response = await fetch('/api' + endpoint, { method, headers: { 'Content-Type': 'application/json' },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    return response.json();
  }, { endpoint, method, body });
}

async function capture(name) {
  await app.windows()[0].screenshot({ path: path.join(run, name), animations: 'disabled', timeout: 15000 });
}

async function chooseContext(container, source, note) {
  await container.locator('.context-picker > summary').click();
  await container.locator('.context-all input').uncheck();
  if (source) await container.locator(`input[data-source-id="${source}"]`).check();
  if (note) await container.locator(`input[data-note-id="${note}"]`).check();
  await container.locator('.context-done').click();
}

(async () => {
  try {
    const endpoint = await provider.start();
    let page = await launch();
    const notebook = await api(page, '/notebooks', 'POST', { title: 'Studio acceptance fixture' });
    const base = `/notebooks/${notebook.id}`;
    await api(page, '/settings', 'PUT', { provider: 'openai_compatible',
      profiles: { openai_compatible: { base_url: endpoint, model: 'synthetic-studio' } },
      embeddings: { provider: 'openai_compatible', base_url: endpoint, model: '' } });
    const note = await api(page, base + '/notes', 'POST', {
      title: 'Launch notes', body: '# Marigold\n\nMarigold launches on October 18.',
    });
    const source = await page.evaluate(async id => {
      const form = new FormData();
      form.append('file', new Blob(['# Excluded\n\nExcluded source says April 2.']), 'excluded.md');
      const response = await fetch(`/api/notebooks/${id}/sources`, { method: 'POST', body: form });
      if (!response.ok) throw new Error(await response.text());
      return response.json();
    }, notebook.id);
    await expect.poll(async () => (await api(page, base + `/sources/${source.id}`)).source.status).toBe('ready');
    await page.reload();

    // A selected saved note is genuine evidence; an excluded source never reaches the writer.
    await chooseContext(page.locator('.chat-context-bar'), null, note.id);
    const input = page.getByLabel('Question about your materials');
    await input.fill('When does Marigold launch?');
    await page.getByRole('button', { name: 'Send question', exact: true }).click();
    await expect(page.locator('.turn')).toHaveCount(1);
    await expect(page.locator('.answer-body')).toContainText('October 18');
    await input.fill('What date was that again?');
    await page.getByRole('button', { name: 'Send question', exact: true }).click();
    await expect(page.locator('.turn')).toHaveCount(2);
    await expect(page.locator('.turn').last().locator('.answer-body')).toContainText('October 18');
    assert.ok(provider.calls.some(call => call.conversation_history?.length), 'Follow-up must include bounded history');
    assert.ok(provider.calls.filter(call => call.evidence).every(call => call.evidence.every(item => !item.quote.includes('April 2'))));
    await page.locator('.turn').last().locator('.citation-buttons button').first().click();
    await expect(page.locator('.note-citation blockquote')).toContainText('October 18');
    await page.getByRole('dialog').getByRole('button', { name: en['common.close'], exact: true }).click();
    const thread = (await api(page, base + '/chats'))[0];
    assert.deepEqual((await api(page, base + `/chats/${thread.id}`)).context, { source_ids: [], note_ids: [note.id] });

    await page.getByRole('tab', { name: en['nav.studio'], exact: true }).click();
    await chooseContext(page.locator('.studio'), null, note.id);
    const materials = [];
    for (const kind of ['summary', 'study_guide', 'review_questions']) {
      await page.getByTestId('studio-format').selectOption(kind);
      await page.getByTestId('studio-generate').click();
      await expect(page.locator('.studio-result .material-view')).toBeVisible();
      await expect(page.locator('.studio-result .material-markdown')).toContainText('October 18');
      await expect.poll(async () => (await api(page, base + '/jobs')).find(job => job.kind === kind)?.status).toBe('completed');
      const job = (await api(page, base + '/jobs')).find(job => job.kind === kind);
      const material = await api(page, base + `/materials/${job.result.material_id}`);
      await expect(page.locator('.studio-result .material-view')).toHaveAttribute('data-material-id', material.id);
      assert.equal(material.answer.validated, true);
      assert.equal(material.answer.citations[0].kind, 'note');
      materials.push(material);
    }
    await capture('01-studio-light-en.png');
    await page.getByTestId('material-copy').click();
    await expect.poll(async () => (await api(page, base + '/notes')).length).toBe(2);
    const exportPath = path.join(run, 'review-questions.md');
    await app.evaluate(({ BrowserWindow }, filename) => {
      globalThis.__studioDownloadState = 'waiting';
      BrowserWindow.getAllWindows()[0].webContents.session.once('will-download', (_event, item) => {
        item.setSavePath(filename);
        item.once('done', (_done, state) => { globalThis.__studioDownloadState = state; });
      });
    }, exportPath);
    await page.getByTestId('material-export').click();
    await expect.poll(() => app.evaluate(() => globalThis.__studioDownloadState)).toBe('completed');
    assert.match(fs.readFileSync(exportPath, 'utf8'), /October 18/);

    // Running cancellation closes the idle HTTP stream and does not publish a material.
    await page.getByTestId('studio-format').selectOption('summary');
    await page.locator('.studio-form textarea').fill('Hold generation for cancellation');
    await page.getByTestId('studio-generate').click();
    await expect.poll(() => provider.calls.some(call => call.question?.includes('Hold generation'))).toBe(true);
    const held = (await api(page, base + '/jobs')).find(job => job.question === 'Hold generation for cancellation');
    await expect(page.locator(`[data-job-id="${held.id}"]`)).toBeVisible();
    await page.locator(`[data-job-id="${held.id}"]`).getByRole('button', { name: en['common.cancel'], exact: true }).click();
    await expect.poll(async () => (await api(page, base + `/jobs/${held.id}`)).status).toBe('cancelled');
    await expect.poll(() => provider.cancelled).toBe(1);
    assert.equal((await api(page, base + '/materials')).length, 3);
    await page.locator(`[data-job-id="${held.id}"]`).getByRole('button', { name: en['jobs.retryCurrent'], exact: true }).click();
    await expect.poll(async () => (await api(page, base + '/jobs')).find(job => job.retry_of === held.id)?.status).toBe('completed');
    assert.equal((await api(page, base + '/materials')).length, 4);

    // Graceful restart leaves unfinished work interrupted, without automatic model replay.
    const interrupted = await api(page, base + '/jobs', 'POST', { request_id: require('node:crypto').randomUUID(), kind: 'summary',
      question: 'Hold generation for restart', language: 'en', context: { source_ids: [], note_ids: [note.id] } });
    await expect.poll(() => provider.calls.filter(call => call.question === 'Hold generation for restart' && !call.claims).length).toBe(1);
    await close();
    const beforeRestart = provider.calls.length;
    page = await launch();
    assert.equal((await api(page, base + `/jobs/${interrupted.id}`)).status, 'interrupted');
    assert.equal(provider.calls.length, beforeRestart, 'Startup must not replay inference');
    assert.equal((await api(page, base + '/materials')).length, 4);
    await page.getByRole('tab', { name: en['nav.artifacts'], exact: true }).click();
    await expect(page.locator('.material-library .note-tabs button')).toHaveCount(4);
    await page.locator('.material-library .note-tabs button').first().click();
    await expect(page.locator('.material-view .material-markdown')).toContainText('October 18');

    await page.getByRole('button', { name: 'Settings', exact: true }).click();
    await page.getByLabel('Interface language').selectOption('ru');
    const dark = page.getByRole('radio', { name: ru['settings.themeDark'], exact: true });
    await dark.click();
    await expect(dark).toBeChecked();
    await page.getByRole('button', { name: ru['common.back'], exact: true }).click();
    await page.getByRole('tab', { name: ru['nav.studio'], exact: true }).click();
    await expect(page.locator(`[data-job-id="${interrupted.id}"]`)).toContainText(ru['jobs.interrupted']);
    await capture('02-studio-dark-ru.png');
    await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].setSize(1000, 680));
    const context = page.locator('.studio .context-picker > summary');
    await context.focus();
    await context.press('Enter');
    await expect(page.locator('.studio .context-picker')).toHaveAttribute('open', '');
    await context.press('Escape');
    await expect(context).toBeFocused();
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Minimum window must not overflow horizontally');
    await capture('03-studio-minimum-window.png');
    assert.deepEqual(provider.errors, []);
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(run, 'result.json'), JSON.stringify({ passed: true, syntheticProvider: true,
      calls: provider.calls.length, materials: materials.map(item => item.kind), errors,
      checks: ['note-only context', 'excluded sources', 'bounded follow-up history', 'note snapshot citation',
        'three Studio formats', 'verified citations', 'editable copy', 'Markdown download', 'HTTP cancellation', 'explicit retry',
        'restart without inference replay', 'persistent library', 'EN/light and RU/dark', 'keyboard context control',
        'minimum window layout', 'isolated Chromium profile'] }, null, 2));
    console.log(JSON.stringify({ passed: true, artifacts: run }));
  } catch (error) {
    if (app) await capture('failure.png').catch(() => {});
    throw error;
  } finally {
    await close();
    await provider.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
