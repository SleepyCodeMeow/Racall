const { chromium } = require('@playwright/test');
const { spawn } = require('node:child_process');
const { randomBytes } = require('node:crypto');
const { createServer } = require('node:net');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

(async () => {
  const run = path.join(root, 'test-results', 'racall-ui-' + Date.now());
  fs.mkdirSync(run, { recursive: true });
  const server = createServer();
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const port = server.address().port;
  await new Promise(resolve => server.close(resolve));
  const origin = `http://127.0.0.1:${port}`;
  const token = randomBytes(32).toString('hex');
  const python = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const log = fs.openSync(path.join(run, 'backend.log'), 'a');
  const backend = spawn(python, ['apps/api/run.py', '--port', String(port), '--data-dir', path.join(run, 'data'), '--web-dir', path.join(root, 'apps/web/out')], {
    cwd: root, env: { ...process.env, OPENNOTEBOOK_SESSION_TOKEN: token, PYTHONUTF8: '1' }, windowsHide: true, stdio: ['ignore', log, log],
  });
  fs.closeSync(log);
  const headers = { Authorization: `Bearer ${token}` };
  const api = async (endpoint, method = 'GET', body) => {
    const response = await fetch(origin + '/api' + endpoint, { method, headers: { ...headers, ...(body && !(body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}) }, body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined });
    if (!response.ok) throw new Error(`${endpoint}: ${response.status} ${await response.text()}`);
    return response.json();
  };
  let browser;
  try {
    let ready = false;
    for (let i = 0; i < 100; i++) {
      try { await api('/settings'); ready = true; break; } catch { await delay(200); }
    }
    assert.ok(ready, 'Backend startup');
    const notebook = await api('/notebooks', 'POST', { title: 'Personal knowledge' });
    await api('/notebooks', 'POST', { title: 'Project ideas' });
    await api('/notebooks', 'POST', { title: 'Books and notes' });
    const materials = [
      ['Связанные заметки.md', '# Связанные заметки\n\nХорошая заметка сохраняет одну мысль и её контекст. Ссылки между заметками помогают возвращаться к идеям и находить новые связи.\n\n## Источники\n\nСохраняйте оригиналы документов вместе с собственными выводами, чтобы можно было проверить цитату.'],
      ['Вопросы для исследования.md', '# Вопросы для исследования\n\nКакие идеи повторяются в разных источниках? Где авторы расходятся? Какие утверждения требуют дополнительных доказательств?'],
      ['Как устроена моя библиотека.md', '# Как устроена моя библиотека\n\nБлокнот объединяет материалы по одной теме. Оригинальные файлы хранятся рядом с заметками в Markdown. Индекс поиска можно перестроить без изменения документов.'],
    ];
    for (const [name, text] of materials) {
      const form = new FormData(); form.append('file', new Blob([text], { type: 'text/markdown' }), name);
      await api(`/notebooks/${notebook.id}/sources`, 'POST', form);
    }
    let sources;
    for (let i = 0; i < 100; i++) {
      sources = await api(`/notebooks/${notebook.id}/sources`);
      if (sources.length === 3 && sources.every(s => s.status === 'ready')) break;
      await delay(200);
    }
    assert.ok(sources.every(s => s.status === 'ready'));
    const chrome = process.env.RACALL_BROWSER_PATH || (process.platform === 'win32' ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : undefined);
    browser = await chromium.launch({ headless: true, ...(chrome ? { executablePath: chrome } : {}) });
    const page = await browser.newPage({ viewport: { width: 1280, height: 820 }, deviceScaleFactor: 1 });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') console.error('Browser:', message.text()); });
    await page.goto(origin + '/#token=' + token);
    await page.getByRole('button', { name: 'Personal knowledge', exact: true }).click();
    await page.getByRole('heading', { name: 'Personal knowledge', exact: true }).waitFor();
    await page.getByLabel("Question about your materials").waitFor();
    await page.evaluate(() => Promise.all([...document.images].map(image => image.decode())));
    assert.equal(await page.title(), 'Racall');
    await page.screenshot({ animations: 'disabled', path: path.join(run, 'workspace.png') });
    const actions = page.getByRole('button', { name: "Material actions", exact: true });
    await actions.click();
    await page.locator('.actions-popover').waitFor();
    await page.screenshot({ animations: 'disabled', path: path.join(run, 'workspace-actions.png') });
    await page.keyboard.press('Escape');
    assert.equal(await actions.getAttribute('aria-expanded'), 'false');
    await actions.click();
    await page.locator('.actions-popover').getByRole('button', { name: "Add materials" }).click();
    await page.locator('.source-drawer:not([hidden])').waitFor();
    await page.screenshot({ animations: 'disabled', path: path.join(run, 'sources.png') });
    await page.getByRole('button', { name: /^Sources/ }).click();
    await page.getByRole('button', { name: "Search", exact: true }).click();
    await page.getByLabel("Question about your materials").fill('оригиналы');
    await page.getByRole('button', { name: "Send question" }).click();
    await page.locator('.search-results button').first().click();
    await page.locator('mark').waitFor();
    assert.equal(await page.getByRole('button', { name: /^Sources/ }).getAttribute('aria-expanded'), 'true');
    await page.screenshot({ animations: 'disabled', path: path.join(run, 'evidence.png') });
    await page.getByRole('button', { name: /^Sources/ }).click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole('tab', { name: "Notes", exact: true }).click();
    await page.getByRole('button', { name: "Create", exact: true }).click();
    await page.getByLabel("Note title").fill('Проверка адаптивного интерфейса');
    await page.getByLabel("Markdown text").fill('Заметка сохранена через настоящий API.');
    await page.getByRole('button', { name: "Save", exact: true }).click();
    await page.getByRole('button', { name: "Saved", exact: true }).waitFor();
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'No mobile horizontal overflow');
    await page.screenshot({ animations: 'disabled', path: path.join(run, 'mobile-notes.png') });
    await page.getByRole('button', { name: 'Personal knowledge', exact: true }).click();
    await page.reload();
    await page.getByRole('button', { name: 'Personal knowledge', exact: true }).click();
    await page.getByRole('heading', { name: "What will we explore today?" }).waitFor();
    await page.screenshot({ animations: 'disabled', path: path.join(run, 'mobile-chat.png') });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'No mobile chat overflow');
    await page.setViewportSize({ width: 1280, height: 820 });
    await page.getByRole('button', { name: 'Settings', exact: true }).click();
    await page.getByLabel('Interface language').waitFor();
    await page.screenshot({ animations: 'disabled', path: path.join(run, 'settings-en.png') });
    await page.getByLabel('Interface language').selectOption('ru');
    await page.getByRole('heading', { name: 'Настройки', exact: true }).waitFor();
    await page.screenshot({ animations: 'disabled', path: path.join(run, 'settings-ru.png') });
    await page.getByLabel('Язык интерфейса').selectOption('en');
    await page.getByRole('heading', { name: 'Settings', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Back', exact: true }).click();
    await page.setViewportSize({ width: 1408, height: 948 });
    await page.addStyleTag({ content: 'body{padding:64px;background:radial-gradient(ellipse at 18% 0%,#ffe7bb 0%,transparent 60%),linear-gradient(130deg,#f1d9bc,#edbc90 55%,#f8e9d5);}.app-shell{width:1280px;height:820px;min-height:820px;border-radius:16px;box-shadow:0 24px 70px #6e421524,0 0 0 1px #ad774317;overflow:hidden;}.navigation{background:#fcfbf9;}' });
    await actions.click();
    await page.locator('.actions-popover').waitFor();
    await page.evaluate(() => Promise.all([...document.images].map(image => image.decode())));
    const screenshot = path.join(root, 'assets/brand/racall-desktop-preview.png');
    await page.screenshot({ animations: 'disabled', path: screenshot });
    assert.equal(errors.length, 0, errors.join('\n'));
    fs.writeFileSync(path.join(run, 'result.json'), JSON.stringify({ passed: true, screenshot, errors, checks: ['real source ingestion', 'mascot loaded', 'actions menu and Escape', 'drawer toggle', 'search citation opens source', 'save note at 390px', 'no horizontal overflow', 'desktop presentation'] }, null, 2));
    console.log(JSON.stringify({ passed: true, run, screenshot }));
  } finally {
    if (browser) await browser.close();
    backend.kill();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
