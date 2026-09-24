const { _electron: electron } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const run = path.join(root, 'test-results', 'languages-' + Date.now());
fs.mkdirSync(run, { recursive: true });
const executable = process.env.OPENNOTEBOOK_TEST_EXE;
const errors = [];
let app;
async function launch(profile) {
  const env = { ...process.env, OPENNOTEBOOK_DATA_DIR: path.join(run, profile), OPENNOTEBOOK_SMOKE_MODE: '1' };
  delete env.ELECTRON_RUN_AS_NODE;
  app = await electron.launch({ ...(executable ? { executablePath: executable, args: ['--disable-gpu'] } : { args: [root, '--disable-gpu'] }), env, timeout: 60000 });
  const page = await app.firstWindow({ timeout: 60000 });
  page.on('pageerror', error => errors.push(error.message));
  await page.locator('.navigation').waitFor();
  return page;
}
async function close() { if (app) { const old = app; app = undefined; await old.close(); } }
(async () => {
  let seedFile, previousSeed;
  try {
    if (executable) {
      seedFile = path.join(path.dirname(executable), ...(process.platform === 'darwin' ? ['..', 'Resources'] : ['resources']), 'installer-language.json');
      previousSeed = fs.existsSync(seedFile) ? fs.readFileSync(seedFile) : null;
      fs.writeFileSync(seedFile, JSON.stringify({ locale: 'en' }));
    }
    let page = await launch('manual');
    assert.equal(await page.locator('html').getAttribute('lang'), 'en');
    await page.getByRole('heading', { name: 'A place for your discoveries.' }).waitFor();
    await page.getByRole('button', { name: 'Settings', exact: true }).click();
    await page.getByLabel('Interface language').selectOption('ru');
    await page.getByRole('heading', { name: 'Настройки', exact: true }).waitFor();
    assert.equal(await page.locator('html').getAttribute('lang'), 'ru');
    await page.getByRole('button', { name: 'Вернуться', exact: true }).click();
    await page.getByRole('button', { name: 'Создать первый блокнот' }).click();
    await page.getByLabel('Название', { exact: true }).fill('Мои заметки / My notes');
    await page.getByRole('button', { name: 'Создать блокнот', exact: true }).click();
    await page.getByRole('tab', { name: 'Заметки', exact: true }).click();
    await page.getByRole('button', { name: 'Создать', exact: true }).click();
    await page.getByLabel('Название заметки').fill('Не переводить / Keep as written');
    const noteBody = 'Это мои слова. These are my words. [[Ссылка]]';
    await page.getByLabel('Текст Markdown').fill(noteBody);
    await page.getByRole('button', { name: 'Сохранить', exact: true }).click();
    await page.getByRole('button', { name: 'Сохранено', exact: true }).waitFor();
    await close();
    page = await launch('manual');
    assert.equal(await page.locator('html').getAttribute('lang'), 'ru', 'Russian must survive a full app restart and new backend port');
    await page.getByRole('button', { name: 'Настройки', exact: true }).click();
    await page.getByLabel('Язык интерфейса').selectOption('en');
    await page.getByRole('heading', { name: 'Settings', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Back', exact: true }).click();
    await page.getByRole('tab', { name: 'Notes', exact: true }).click();
    await page.getByRole('button', { name: 'Не переводить / Keep as written', exact: true }).click();
    assert.equal(await page.getByLabel('Markdown text').inputValue(), noteBody);
    await page.getByRole('tab', { name: 'Research', exact: true }).click();
    await page.getByLabel('Research topic').fill('What do these materials say?');
    await page.getByRole('button', { name: 'Start research', exact: true }).click();
    await page.getByRole('alert').filter({ hasText: 'Enter a model name in AI settings' }).waitFor();
    await close();
    if (seedFile) {
      fs.writeFileSync(seedFile, JSON.stringify({ locale: 'ru' }));
      page = await launch('from-installer');
      assert.equal(await page.locator('html').getAttribute('lang'), 'ru', 'Installer choice must seed a fresh profile');
      await close();
      page = await launch('manual');
      assert.equal(await page.locator('html').getAttribute('lang'), 'en', 'Updated installer seed must not override the saved in-app choice');
      await close();
    }
    assert.equal(errors.length, 0, errors.join('\n'));
    const result = { passed: true, packaged: !!executable, errors, checks: ['English default', 'live Russian switch', 'full app restart', 'live English switch', 'original note preserved', 'localized provider error', ...(seedFile ? ['Russian installer seed', 'upgrade preserves manual selection'] : [])] };
    fs.writeFileSync(path.join(run, 'result.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify({ ...result, artifacts: run }));
  } finally {
    await close();
    if (seedFile) { if (previousSeed) fs.writeFileSync(seedFile, previousSeed); else if (fs.existsSync(seedFile)) fs.unlinkSync(seedFile); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
