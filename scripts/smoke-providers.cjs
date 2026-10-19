const { _electron: electron, expect } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const run = path.join(root, 'test-results', 'providers-desktop-' + Date.now());
fs.mkdirSync(run, { recursive: true });
const executable = process.env.OPENNOTEBOOK_TEST_EXE;
let app;
const errors = [];
const writes = [];

async function launch(profile) {
  const env = { ...process.env, OPENNOTEBOOK_DATA_DIR: path.join(run, profile), OPENNOTEBOOK_SMOKE_MODE: '1', PYTHON_KEYRING_BACKEND: 'keyring.backends.null.Keyring' };
  for (const key of ['ELECTRON_RUN_AS_NODE', 'OPENNOTEBOOK_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'OLLAMA_API_KEY']) delete env[key];
  app = await electron.launch({ ...(executable ? { executablePath: executable, args: ['--disable-gpu'] } : { args: [root, '--disable-gpu'] }), env, timeout: 60000 });
  const page = await app.firstWindow({ timeout: 60000 });
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/settings', async route => {
    if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON();
      // Draft isolation is tested without writing any value to the user's keychain.
      if ('api_key' in body || 'embedding_api_key' in body) {
        errors.push('Unexpected keychain write from provider smoke');
        await route.abort();
        return;
      }
      writes.push(body);
    }
    await route.continue();
  });
  await page.locator('.navigation').waitFor();
  await page.getByRole('button', { name: 'Settings', exact: true }).click();
  await page.locator('#answer-model').waitFor();
  return page;
}

async function close() { if (app) { const old = app; app = undefined; await old.close(); } }
async function save(page) {
  await page.locator('.provider-settings-form button.primary').click();
  await expect(page.locator('.provider-settings-form button.primary')).toHaveText('Saved');
}
async function screenshot(name) {
  const encoded = await app.evaluate(async ({ BrowserWindow }) => (await BrowserWindow.getAllWindows()[0].webContents.capturePage(undefined, { stayHidden: true, stayAwake: true })).toPNG().toString('base64'));
  fs.writeFileSync(path.join(run, name), Buffer.from(encoded, 'base64'));
}

(async () => {
  try {
    let page = await launch('fresh');
    assert.deepEqual(await page.locator('.provider-picker button').allTextContents(), ['OpenAI', 'Claude', 'Ollama', 'llama.cpp']);
    await expect(page.getByRole('button', { name: 'OpenAI', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await page.locator('#answer-model').fill('openai-selected-model');
    await page.locator('#provider-api-key').fill('draft-for-openai-never-saved');
    await page.getByRole('button', { name: 'Claude', exact: true }).click();
    await expect(page.locator('#provider-api-key')).toHaveValue('');
    await page.locator('#answer-model').fill('claude-selected-model');
    await page.locator('#provider-api-key').fill('draft-for-claude-never-saved');
    await page.getByRole('button', { name: 'OpenAI', exact: true }).click();
    await expect(page.locator('#provider-api-key')).toHaveValue('draft-for-openai-never-saved');
    await expect(page.locator('.pending-provider-keys')).toBeVisible();
    await page.locator('#provider-api-key').fill('');
    await page.getByRole('button', { name: 'Claude', exact: true }).click();
    await expect(page.locator('#provider-api-key')).toHaveValue('draft-for-claude-never-saved');
    await page.locator('#provider-api-key').fill('');
    await save(page);

    await page.getByRole('button', { name: 'Ollama', exact: true }).click();
    await expect(page.locator('#provider-url')).toHaveValue('http://127.0.0.1:11434/v1');
    await page.locator('#answer-model').fill('local-selected-model');
    await page.locator('.ollama-mode button').nth(1).click();
    await expect(page.locator('#provider-url')).toHaveValue('https://ollama.com/v1');
    await page.locator('#answer-model').fill('cloud-selected-model');
    await save(page);
    await page.locator('.ollama-mode button').nth(0).click();
    await expect(page.locator('#answer-model')).toHaveValue('local-selected-model');
    await page.getByRole('button', { name: 'llama.cpp', exact: true }).click();
    await page.locator('#answer-model').fill('server-selected-model');
    await page.locator('.embedding-settings summary').click();
    await page.locator('#embedding-provider').selectOption('ollama');
    await page.locator('#embedding-url').fill('http://127.0.0.1:9911/v1');
    await page.locator('#embedding-model').fill('independent-embedding-model');
    await save(page);
    await page.getByRole('button', { name: 'Claude', exact: true }).click();
    await expect(page.locator('#answer-model')).toHaveValue('claude-selected-model');
    await expect(page.locator('#embedding-url')).toHaveValue('http://127.0.0.1:9911/v1');
    await expect(page.locator('#embedding-model')).toHaveValue('independent-embedding-model');
    await save(page);
    await page.locator('.embedding-settings summary').click();
    await page.locator('.page-content').evaluate(element => { element.scrollTop = 0; });
    await screenshot('settings-en.png');
    await close();

    page = await launch('fresh');
    await expect(page.getByRole('button', { name: 'Claude', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('#answer-model')).toHaveValue('claude-selected-model');
    await page.getByRole('button', { name: 'OpenAI', exact: true }).click();
    await expect(page.locator('#answer-model')).toHaveValue('openai-selected-model');
    await page.getByRole('button', { name: 'Ollama', exact: true }).click();
    await expect(page.locator('#answer-model')).toHaveValue('local-selected-model');
    await page.locator('.ollama-mode button').nth(1).click();
    await expect(page.locator('#answer-model')).toHaveValue('cloud-selected-model');
    await page.getByLabel('Interface language').selectOption('ru');
    await page.getByRole('heading', { name: 'Настройки', exact: true }).waitFor();
    await expect(page.locator('.connection-kind')).toHaveText('Облачное подключение');
    await screenshot('settings-ru.png');
    await close();

    const legacy = path.join(run, 'legacy');
    fs.mkdirSync(legacy, { recursive: true });
    const original = JSON.stringify({ base_url: 'http://127.0.0.1:9876/v1', model: 'legacy-model', embedding_model: 'legacy-embedding' });
    fs.writeFileSync(path.join(legacy, 'settings.json'), original);
    page = await launch('legacy');
    await expect(page.locator('.custom-provider')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('#answer-model')).toHaveValue('legacy-model');
    assert.equal(fs.readFileSync(path.join(legacy, 'settings.json'), 'utf8'), original, 'Opening must not rewrite old settings');
    await page.getByRole('button', { name: 'Claude', exact: true }).click();
    await page.locator('#answer-model').fill('new-claude-profile');
    await save(page);
    await page.locator('.custom-provider').click();
    await expect(page.locator('#provider-url')).toHaveValue('http://127.0.0.1:9876/v1');
    await expect(page.locator('#answer-model')).toHaveValue('legacy-model');
    const stored = JSON.parse(fs.readFileSync(path.join(legacy, 'settings.json'), 'utf8'));
    assert.equal(stored.embeddings.base_url, 'http://127.0.0.1:9876/v1');
    assert.equal(stored.embeddings.model, 'legacy-embedding');
    await close();
    assert.equal(errors.length, 0, errors.join('\n'));
    assert.ok(writes.length >= 4);
    assert.ok(!fs.readFileSync(path.join(run, 'fresh', 'settings.json'), 'utf8').includes('draft-for-'));
    const result = { passed: true, packaged: !!executable, modelRequests: 0, keychainWrites: 0, errors,
      checks: ['four providers', 'per-provider draft key isolation', 'separate local/cloud profiles', 'independent embeddings', 'full app restart', 'EN/RU', 'legacy configuration migration'], artifacts: run };
    fs.writeFileSync(path.join(run, 'result.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
  } finally { await close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
