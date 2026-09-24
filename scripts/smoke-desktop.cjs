const { _electron: electron } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const root = path.resolve(__dirname, '..');
  const run = path.join(root, 'test-results', 'desktop-' + Date.now());
  fs.mkdirSync(run, { recursive: true });
  const env = { ...process.env, OPENNOTEBOOK_DATA_DIR: path.join(run, 'data'), OPENNOTEBOOK_SMOKE_MODE: '1' };
  delete env.ELECTRON_RUN_AS_NODE;
  const options = process.env.OPENNOTEBOOK_TEST_EXE ? { executablePath: process.env.OPENNOTEBOOK_TEST_EXE, args: ['--disable-gpu'] } : { args: [root, '--disable-gpu'] };
  const app = await electron.launch({ ...options, env, timeout: 60000 });
  const errors = [];
  const capture = async (filename) => {
    const encoded = await app.evaluate(async ({ BrowserWindow }) => {
      const image = await BrowserWindow.getAllWindows()[0].webContents.capturePage(undefined, { stayHidden: true, stayAwake: true });
      return image.toPNG().toString('base64');
    });
    fs.writeFileSync(path.join(run, filename), Buffer.from(encoded, 'base64'));
  };
  try {
    const page = await app.firstWindow({ timeout: 60000 });
    page.on('pageerror', error => errors.push(error.message));
    await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].webContents.setBackgroundThrottling(false));
    await page.getByRole('button', { name: 'Settings', exact: true }).click();
    await page.getByLabel('Interface language').selectOption('ru');
    await page.getByRole('heading', { name: 'Настройки', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Вернуться', exact: true }).click();
    await page.locator('.notebook-list .skeleton').waitFor({ state: 'hidden', timeout: 15000 });
    await page.getByRole('button', { name: 'Создать первый блокнот' }).click();
    await page.getByLabel('Название', { exact: true }).fill('Архитектура знаний');
    await page.getByRole('button', { name: 'Создать блокнот', exact: true }).click();
    await page.getByRole('heading', { name: 'Архитектура знаний', exact: true }).waitFor();
    await capture('01-workspace.png');
    await page.getByRole('button', { name: /^Источники/ }).click();
    await page.locator('input[type=file]').setInputFiles({ name: 'План проекта.md', mimeType: 'text/markdown', buffer: Buffer.from('# Архитектура\n\nOpenNotebook хранит оригиналы локально. Кодовое имя проекта — Marigold.\n\n## Сроки\n\nПервый выпуск запланирован на 18 октября.\n') });
    await page.getByText('1 источник готов', { exact: true }).waitFor({ timeout: 30000 });
    await page.getByRole('button', { name: /^Источники/ }).click();
    await page.getByRole('button', { name: 'Поиск', exact: true }).click();
    await page.getByLabel('Вопрос по материалам').fill('Marigold');
    await page.getByRole('button', { name: 'Отправить вопрос' }).click();
    await page.locator('.search-results button').first().waitFor();
    await page.locator('.search-results button').first().click();
    await page.locator('mark').waitFor();
    assert.match(await page.locator('mark').innerText(), /Marigold/);
    await capture('02-evidence.png');
    await page.getByRole('button', { name: 'Закрыть источник' }).click();
    await page.getByRole('tab', { name: 'Заметки', exact: true }).click();
    await page.getByRole('button', { name: 'Создать', exact: true }).click();
    await page.getByLabel('Название заметки').fill('Мои выводы');
    await page.getByLabel('Текст Markdown').fill('# Главная мысль\n\nЗнания принадлежат пользователю. [[Следующий шаг]]');
    await page.getByRole('button', { name: 'Сохранить', exact: true }).click();
    await page.getByRole('button', { name: 'Сохранено', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Предпросмотр' }).click();
    await page.getByRole('heading', { name: 'Главная мысль' }).waitFor();
    await capture('03-notes.png');
    await page.getByRole('button', { name: 'Подключить AI' }).click();
    await page.locator('.config-block').filter({ hasText: 'mcpServers' }).waitFor();
    assert.match(await page.locator('.config-block').innerText(), /--notebook/);
    await page.getByRole('button', { name: 'Настройки', exact: true }).click();
    await page.getByRole('button', { name: 'Ollama', exact: true }).click();
    await page.getByLabel('Модель ответов', { exact: true }).fill('test-local-model');
    await page.getByRole('button', { name: 'Сохранить настройки' }).click();
    await page.getByRole('button', { name: 'Сохранено', exact: true }).waitFor();
    assert.equal(errors.length, 0, errors.join('\n'));
    fs.writeFileSync(path.join(run, 'result.json'), JSON.stringify({ passed: true, errors, scenarios: ['create notebook', 'upload Markdown', 'search', 'exact passage viewer', 'save Markdown', 'preview wikilinks', 'MCP configuration', 'save Ollama settings'] }, null, 2));
    console.log(JSON.stringify({ passed: true, artifacts: run }));
  } catch (error) {
    console.error('Renderer errors:', errors);
    const page = app.windows()[0];
    if (page) { await page.screenshot({ path: path.join(run, 'failure.png') }).catch(() => {}); console.error(await page.locator('body').innerText().catch(() => '')); }
    throw error;
  } finally { await app.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
