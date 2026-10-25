const assert = require('node:assert/strict');
const path = require('node:path');
const { randomUUID, createHash } = require('node:crypto');
const { expect } = require('@playwright/test');
const { studioProvider } = require('../smoke/studio-provider.cjs');
const ru = require('../../apps/shared/locales/ru.json');

const OLD_SOURCE = '# Marigold\n\nMarigold launches on October 18.\n';
const NEW_SOURCE = '# Marigold\n\nMarigold launches on November 22.\n';
const NOTE_BODY =
  '# Upgrade notes\n\nMarigold launches on October 18.\n\nСохранить заметку и [[связь]].';
const QUESTION = 'When does Marigold launch?';

/** All fixture records are created by the real installed 0.2 API, not hand-written schemas. */
async function seedBaseline(desktop, endpoint) {
  assert.deepEqual(await desktop.api('/preferences'), { locale: 'ru' });
  await desktop.api('/settings', 'PUT', {
    base_url: endpoint,
    model: 'synthetic-upgrade',
    embedding_model: '',
  });
  const notebook = await desktop.api('/notebooks', 'POST', { title: 'Upgrade notebook' });
  const base = `/notebooks/${notebook.id}`;
  const note = await desktop.api(base + '/notes', 'POST', {
    title: 'Upgrade notes',
    body: NOTE_BODY,
  });
  const source = await desktop.upload(base + '/sources', OLD_SOURCE);
  await expect
    .poll(async () => (await desktop.api(base + `/sources/${source.id}`)).source.status, {
      timeout: 60000,
    })
    .toBe('ready');
  const thread = await desktop.api(base + '/chats', 'POST', {
    title: 'Preserved 0.2 conversation',
  });
  const turn = await desktop.api(base + `/chats/${thread.id}/turns`, 'POST', {
    question: QUESTION,
    mode: 'ask',
    request_id: randomUUID(),
  });
  assert.equal(turn.status, 'completed');
  assert.equal(turn.answer.validated, true);
  const research = await desktop.api(base + '/research', 'POST', { question: QUESTION });
  assert.equal(research.status, 'completed');
  assert.equal(research.answer.validated, true);
  const report = await desktop.api(base + `/research/${research.id}/save`, 'POST');
  assert.match(report.body, /October 18/);
  assert.ok(research.answer.citations.length > 0);
  assert.equal(research.answer.citations[0].version, source.version);
  await desktop.upload(base + `/sources/${source.id}`, NEW_SOURCE, 'PUT');
  const nextVersion = createHash('sha256').update(NEW_SOURCE).digest('hex');
  await expect
    .poll(async () => (await desktop.api(base + `/sources/${source.id}`)).source.version, {
      timeout: 60000,
    })
    .toBe(nextVersion);
  const currentSource = (await desktop.api(base + `/sources/${source.id}`)).source;
  assert.equal(currentSource.status, 'ready');
  const trashed = await desktop.api('/notebooks', 'POST', { title: 'Preserved notebook trash' });
  await desktop.api(`/notebooks/${trashed.id}/notes`, 'POST', {
    title: 'Trashed note',
    body: 'Still belongs to its owner.',
  });
  await desktop.api(`/notebooks/${trashed.id}`, 'DELETE');
  // Exercise both supported choices, then preserve Russian against an English 0.3 install seed.
  await desktop.api('/preferences', 'PUT', { locale: 'en' });
  await desktop.api('/preferences', 'PUT', { locale: 'ru' });
  await desktop.api('/appearance', 'PUT', { theme: 'dark' });
  const settings = await desktop.api('/settings');
  await desktop.page.reload();
  await expect(desktop.page.locator('html')).toHaveAttribute('lang', 'ru');
  await expect(desktop.page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await desktop.capture('01-baseline-02.png');
  return {
    notebook,
    note,
    source,
    currentSource,
    thread,
    turn,
    research,
    report,
    trashed,
    settings,
  };
}

async function assertLegacyData(desktop, fixture) {
  const {
    notebook,
    note,
    source,
    currentSource,
    thread,
    turn,
    research,
    report,
    trashed,
    settings,
  } = fixture;
  const base = `/notebooks/${notebook.id}`;
  assert.ok((await desktop.api('/notebooks')).some((item) => item.id === notebook.id));
  assert.ok((await desktop.api('/notebooks/trash')).some((item) => item.id === trashed.id));
  const restoredNote = (await desktop.api(base + '/notes')).find((item) => item.id === note.id);
  for (const key of ['id', 'title', 'body', 'revision'])
    assert.deepEqual(restoredNote[key], note[key]);
  const restoredSource = (await desktop.api(base + `/sources/${source.id}`)).source;
  assert.equal(restoredSource.version, currentSource.version);
  const versions = await desktop.api(base + `/sources/${source.id}/versions`);
  assert.deepEqual(
    versions.map((item) => item.version).sort(),
    [source.version, currentSource.version].sort(),
  );
  assert.equal(
    await desktop.text(base + `/sources/${source.id}/versions/${source.version}/original`),
    OLD_SOURCE,
  );
  assert.equal(
    await desktop.text(base + `/sources/${source.id}/versions/${currentSource.version}/original`),
    NEW_SOURCE,
  );
  const historical = await desktop.api(base + `/sources/${source.id}/versions/${source.version}`);
  assert.equal(historical.source.version, source.version);
  for (const citation of research.answer.citations) {
    assert.equal(citation.source_id, source.id);
    assert.equal(citation.version, source.version);
    const element = historical.document.elements[citation.location.element];
    assert.equal(
      element.text.slice(citation.location.offset_start, citation.location.offset_end),
      citation.quote,
    );
  }
  const conversation = await desktop.api(base + `/chats/${thread.id}`);
  assert.equal(conversation.turns.length, 1);
  assert.deepEqual(conversation.turns[0], turn);
  const savedResearch = (await desktop.api(base + '/research')).find(
    (item) => item.id === research.id,
  );
  assert.deepEqual(savedResearch, research);
  const material = (await desktop.api(base + '/materials')).find(
    (item) => item.id === 'legacy:' + report.id,
  );
  assert.ok(material, 'Earlier report must be exposed by the 0.3 material library.');
  assert.equal(material.legacy, true);
  assert.equal(material.body, report.body);
  assert.deepEqual(material.answer.citations, research.answer.citations);
  const exported = await desktop.text(
    base + `/materials/${encodeURIComponent(material.id)}/export`,
  );
  assert.equal(exported, report.body);
  const upgradedSettings = await desktop.api('/settings');
  for (const key of [
    'provider',
    'profiles',
    'embeddings',
    'base_url',
    'model',
    'embedding_model',
  ]) {
    assert.deepEqual(
      upgradedSettings[key],
      settings[key],
      `Saved provider setting changed: ${key}`,
    );
  }
  assert.deepEqual(await desktop.api('/preferences'), { locale: 'ru' });
  assert.deepEqual(await desktop.api('/appearance'), { theme: 'dark' });
  await expect(desktop.page.locator('html')).toHaveAttribute('lang', 'ru');
  await expect(desktop.page.locator('html')).toHaveAttribute('data-theme', 'dark');
  assert.equal(await desktop.app.evaluate(({ nativeTheme }) => nativeTheme.themeSource), 'dark');
  return material;
}

async function exerciseUpgradedUI(desktop, fixture) {
  const page = desktop.page;
  const base = `/notebooks/${fixture.notebook.id}`;
  await page.getByRole('button', { name: fixture.notebook.title, exact: true }).click();
  await page.getByRole('tab', { name: ru['nav.artifacts'], exact: true }).click();
  await page.locator('.material-library .note-tabs button').filter({ hasText: QUESTION }).click();
  await expect(page.locator('.material-view')).toHaveAttribute(
    'data-material-id',
    'legacy:' + fixture.report.id,
  );
  await expect(page.locator('.material-heading')).toContainText(ru['materials.legacy']);
  const exported = await desktop.downloadLegacy(path.join(desktop.run, 'legacy-report.md'));
  assert.equal(exported, fixture.report.body);
  await page.locator('.material-view .evidence-list button').first().click();
  await expect(page.locator('.detail-panel .draft-notice')).toContainText(
    ru['source.previousVersion'],
  );
  await expect(page.locator('.detail-panel mark')).toContainText('October 18');
  await expect(page.getByLabel(ru['source.version']).locator('option')).toHaveCount(2);
  await desktop.capture('02-upgraded-historical-citation.png');
  await page.getByRole('button', { name: ru['source.close'], exact: true }).click();
  await page.getByRole('button', { name: ru['settings.title'], exact: true }).click();
  await page.locator('#interface-language').selectOption('en');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await page.locator('.theme-choice input[value="light"]').check();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.locator('.theme-choice input[value="dark"]').check();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.locator('#interface-language').selectOption('ru');
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
  await expect(
    page.getByRole('heading', { name: ru['settings.title'], exact: true }),
  ).toBeVisible();
  await page.getByRole('tab', { name: ru['nav.studio'], exact: true }).click();
  const studio = page.locator('.studio');
  await studio.locator('.context-picker > summary').click();
  await studio.locator('.context-all input').uncheck();
  await studio.locator(`input[data-note-id="${fixture.note.id}"]`).check();
  await studio.locator('.context-done').click();
  await page.getByTestId('studio-format').selectOption('summary');
  await page.getByTestId('studio-generate').click();
  await expect(page.locator('.studio-result .material-view')).toBeVisible({ timeout: 60000 });
  const materialId = await page
    .locator('.studio-result .material-view')
    .getAttribute('data-material-id');
  const material = await desktop.api(base + `/materials/${materialId}`);
  assert.equal(material.kind, 'summary');
  assert.equal(material.answer.validated, true);
  assert.ok(
    material.answer.citations.every(
      (item) => item.kind === 'note' && item.note_id === fixture.note.id,
    ),
  );
  const jobs = await desktop.api(base + '/jobs');
  assert.equal(jobs.find((item) => item.result?.material_id === materialId)?.status, 'completed');
  await desktop.capture('03-upgraded-studio.png');
  return materialId;
}

module.exports = {
  createProvider: studioProvider,
  seedBaseline,
  assertLegacyData,
  exerciseUpgradedUI,
};
