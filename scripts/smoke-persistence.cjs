const { _electron: electron, expect } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const root = path.resolve(__dirname, '..');
const run = path.join(root, 'test-results', 'persistence-' + Date.now());
const data = path.join(run, 'data');
const en = JSON.parse(fs.readFileSync(path.join(root, 'apps/shared/locales/en.json'), 'utf8'));
const ru = JSON.parse(fs.readFileSync(path.join(root, 'apps/shared/locales/ru.json'), 'utf8'));
fs.mkdirSync(data, { recursive: true });
const errors = [];
let app, server;
async function launch() {
  const env = {
    ...process.env,
    OPENNOTEBOOK_DATA_DIR: data,
    OPENNOTEBOOK_SMOKE_MODE: '1',
  };
  delete env.ELECTRON_RUN_AS_NODE;
  app = await electron.launch({
    ...(process.env.OPENNOTEBOOK_TEST_EXE
      ? {
          executablePath: process.env.OPENNOTEBOOK_TEST_EXE,
          args: ['--disable-gpu'],
        }
      : { args: [root, '--disable-gpu'] }),
    env,
    timeout: 60000,
  });
  const page = await app.firstWindow({ timeout: 60000 });
  page.on('pageerror', (e) => errors.push(e.message));
  // Electron handles beforeunload with a native dialog; CDP cannot dismiss it.
  page.on('dialog', async (dialog) => {
    if (dialog.type() !== 'beforeunload') await dialog.dismiss();
  });
  await app.evaluate(({ BrowserWindow }) =>
    BrowserWindow.getAllWindows()[0].webContents.setBackgroundThrottling(false),
  );
  await page.locator('.navigation').waitFor();
  return page;
}
async function close(force = false) {
  if (!app) return;
  if (force)
    await app.evaluate(({ BrowserWindow }) =>
      BrowserWindow.getAllWindows().forEach((w) => w.destroy()),
    );
  const old = app;
  app = undefined;
  await old.close();
}
async function api(page, endpoint, method = 'GET', body) {
  return page.evaluate(
    async ({ endpoint, method, body }) => {
      const response = await fetch('/api' + endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
      });
      if (!response.ok) throw new Error('HTTP ' + response.status + ': ' + (await response.text()));
      return response.json();
    },
    { endpoint, method, body },
  );
}
async function capture(name) {
  const encoded = await app.evaluate(async ({ BrowserWindow }) =>
    (
      await BrowserWindow.getAllWindows()[0].webContents.capturePage(undefined, {
        stayHidden: true,
        stayAwake: true,
      })
    )
      .toPNG()
      .toString('base64'),
  );
  fs.writeFileSync(path.join(run, name), Buffer.from(encoded, 'base64'));
}
(async () => {
  try {
    let modelCalls = 0;
    server = http.createServer((request, response) => {
      let text = '';
      request.on('data', (chunk) => (text += chunk));
      request.on('end', () => {
        try {
          modelCalls++;
          const payload = JSON.parse(text);
          const input = JSON.parse(payload.messages[1].content);
          const result = input.claims
            ? { supported_claim_ids: [input.claims[0].claim_id] }
            : {
                claims: [
                  {
                    text: 'Marigold launches on October 18.',
                    evidence_ids: [input.evidence.find((e) => e.quote.includes('October 18')).id],
                  },
                ],
                message: '',
              };
          assert.equal(payload.stream, true, 'Packaged completion must request streaming');
          response.writeHead(200, { 'Content-Type': 'text/event-stream' });
          const send = (delta, finish_reason = null) =>
            response.write(
              `data: ${JSON.stringify({ choices: [{ index: 0, delta, finish_reason }] })}\n\n`,
            );
          send({ role: 'assistant', reasoning: 'Internal draft must never become an answer.' });
          const content = JSON.stringify(result);
          const split = Math.floor(content.length / 2);
          send({ content: content.slice(0, split) });
          send({ content: content.slice(split) });
          send({}, 'stop');
          response.end('data: [DONE]\n\n');
        } catch (e) {
          response.writeHead(500);
          response.end(String(e));
        }
      });
    });
    await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
    let page = await launch();
    const notebook = await api(page, '/notebooks', 'POST', {
      title: 'Persistent research',
    });
    const empty = await api(page, '/notebooks', 'POST', {
      title: 'Separate notebook',
    });
    await api(page, '/settings', 'PUT', {
      base_url: `http://127.0.0.1:${server.address().port}/v1`,
      model: 'deterministic-test',
      embedding_model: '',
    });
    const source = await page.evaluate(async (id) => {
      const form = new FormData();
      form.append(
        'file',
        new Blob(['# Marigold\n\nMarigold launches on October 18.']),
        'mission.md',
      );
      return (
        await fetch(`/api/notebooks/${id}/sources`, {
          method: 'POST',
          body: form,
        })
      ).json();
    }, notebook.id);
    await expect
      .poll(
        async () =>
          (await api(page, `/notebooks/${notebook.id}/sources/${source.id}`)).source.status,
      )
      .toBe('ready');
    await page.reload();
    await page.getByLabel('Question about your materials').fill('When does Marigold launch?');
    await page.getByRole('button', { name: 'Send question', exact: true }).click();
    await page
      .locator('.answer-body')
      .getByText('Marigold launches on October 18.', { exact: false })
      .waitFor();
    await expect(page.getByRole('button', { name: 'Rename', exact: true })).toBeEnabled();
    await page.getByRole('button', { name: 'Rename', exact: true }).click();
    await page.getByLabel('Chat name').fill('Mission questions');
    await page.locator('.chat-rename').getByRole('button', { name: 'Save', exact: true }).click();
    const firstThread = (await api(page, `/notebooks/${notebook.id}/chats`))[0].id;
    await page.getByRole('button', { name: 'New chat', exact: true }).click();
    await expect(page.getByLabel('Question about your materials')).toBeEnabled();
    await page.getByRole('button', { name: 'Search', exact: true }).click();
    await page.getByLabel('Question about your materials').fill('Marigold');
    await page.getByRole('button', { name: 'Send question', exact: true }).click();
    await page.locator('.search-results button').first().waitFor();
    const oldOrigin = new URL(page.url()).origin;
    const research = {
      id: require('node:crypto').randomUUID(),
      question: 'Interrupted research fixture',
      status: 'running',
      created_at: new Date().toISOString(),
      steps: [],
    };
    fs.writeFileSync(
      path.join(data, 'notebooks', notebook.id, 'research', research.id + '.json'),
      JSON.stringify(research),
    );
    await close();
    page = await launch();
    await page.getByLabel('Chat history').selectOption(firstThread);
    await page
      .locator('.answer-body')
      .getByText('Marigold launches on October 18.', { exact: false })
      .waitFor();
    await page.locator('.citation-buttons button').first().click();
    await page.locator('mark').filter({ hasText: 'October 18' }).waitFor();
    assert.equal(modelCalls, 2, 'Restart must not call the model again');
    await capture('01-restored-chat.png');
    await page.getByRole('button', { name: 'Close source', exact: true }).click();
    await page.getByRole('tab', { name: en['nav.research'], exact: true }).click();
    const interruptedResearch = page
      .locator('button.research-history')
      .filter({ hasText: research.question });
    await expect(interruptedResearch).toContainText(en['research.interrupted']);
    await interruptedResearch.click();
    await expect(page.getByText(en['research.interruptedDetail'], { exact: true })).toBeVisible();
    assert.equal(
      (await api(page, `/notebooks/${notebook.id}/research`)).find(
        (item) => item.id === research.id,
      ).status,
      'interrupted',
    );
    assert.equal(
      modelCalls,
      2,
      'Research recovery and opening details must not replay model requests',
    );
    await page.getByRole('tab', { name: 'Notes', exact: true }).click();
    await page.getByRole('button', { name: 'Create', exact: true }).click();
    await page.getByLabel('Note title').fill('Daily note');
    await page.getByLabel('Markdown text').fill('Autosaved without pressing Save. [[Next step]]');
    await page.getByRole('button', { name: 'Saved', exact: true }).waitFor();
    const saved = (await api(page, `/notebooks/${notebook.id}/notes`))[0];
    // A title-less edit cannot be autosaved. Every workspace exit must leave
    // the mounted editor intact instead of relying on fire-and-forget cleanup.
    const unsavedBody = 'Keep this title-less draft when navigation is blocked.';
    await page.getByLabel('Note title').fill('');
    await page.getByLabel('Markdown text').fill(unsavedBody);
    const blockedExits = [
      page.locator('.global-nav button'),
      page.locator('.nav-bottom > button'),
      page.locator('.provider-button'),
      page.locator('.new-notebook'),
      page.getByRole('button', { name: 'Separate notebook', exact: true }),
    ];
    for (const exit of blockedExits) {
      await exit.click();
      await expect(page.locator('.error-banner')).toContainText(en['notebook.unsaved']);
      await expect(page.getByRole('tab', { name: 'Notes', exact: true })).toHaveAttribute(
        'aria-selected',
        'true',
      );
      await expect(page.getByLabel('Note title')).toHaveValue('');
      await expect(page.getByLabel('Markdown text')).toHaveValue(unsavedBody);
      await expect(page.locator('.apps-page, .settings, .modal-backdrop')).toHaveCount(0);
      await page.locator('.error-banner button').click();
    }
    assert.equal(
      (await api(page, '/notebooks')).length,
      2,
      'Blocked new-notebook navigation must not create a notebook',
    );
    assert.equal(
      (await api(page, `/notebooks/${notebook.id}/notes`))[0].body,
      saved.body,
      'A title-less edit must not overwrite the saved note',
    );
    await page.getByLabel('Note title').fill(saved.title);
    await page.getByLabel('Markdown text').fill(saved.body);
    await page.getByRole('button', { name: 'Saved', exact: true }).waitFor();
    // A late create response must recheck edits made after closing its dialog.
    await page.evaluate(() => {
      const original = window.fetch.bind(window);
      let release;
      const gate = new Promise((resolve) => {
        release = resolve;
      });
      window.__releaseNotebookCreation = release;
      window.__notebookCreationEntered = false;
      window.__restoreNotebookFetch = () => {
        window.fetch = original;
      };
      window.fetch = async (...args) => {
        const response = await original(...args);
        if (String(args[0]).endsWith('/api/notebooks') && args[1]?.method === 'POST') {
          window.__notebookCreationEntered = true;
          await gate;
        }
        return response;
      };
    });
    await page.locator('.new-notebook').click();
    await page.getByLabel(en['notebook.name'], { exact: true }).fill('Delayed creation fixture');
    await page.getByRole('button', { name: en['notebook.create'], exact: true }).click();
    await page.waitForFunction(() => window.__notebookCreationEntered);
    await page.locator('.modal-close').click();
    await page.getByLabel('Note title').fill('');
    await page.getByLabel('Markdown text').fill(unsavedBody);
    await page.evaluate(() => window.__releaseNotebookCreation());
    await expect(page.locator('.error-banner')).toContainText(en['notebook.unsaved']);
    await expect(page.locator('.workspace-header h1')).toHaveText(notebook.title);
    await expect(page.getByLabel('Note title')).toHaveValue('');
    await expect(page.getByLabel('Markdown text')).toHaveValue(unsavedBody);
    await page.evaluate(() => window.__restoreNotebookFetch());
    const delayedNotebook = (await api(page, '/notebooks')).find(
      (item) => item.title === 'Delayed creation fixture',
    );
    assert.ok(
      delayedNotebook,
      'Creation may finish, but its late navigation must respect new edits',
    );
    await api(page, `/notebooks/${delayedNotebook.id}`, 'DELETE');
    await page.locator('.error-banner button').click();
    await page.getByLabel('Note title').fill(saved.title);
    await page.getByLabel('Markdown text').fill(saved.body);
    await page.getByRole('button', { name: 'Saved', exact: true }).waitFor();
    // Delay the renderer's acknowledgement without bypassing Electron's auth headers.
    await page.evaluate(() => {
      const original = window.fetch.bind(window);
      let used = false;
      let release;
      const gate = new Promise((resolve) => {
        release = resolve;
      });
      window.__releaseAutosave = release;
      window.__autosaveEntered = false;
      window.fetch = async (...args) => {
        const response = await original(...args);
        if (!used && String(args[0]).endsWith('/notes/autosave')) {
          used = true;
          window.__autosaveEntered = true;
          await gate;
        }
        return response;
      };
      window.__restoreFetch = () => {
        window.fetch = original;
      };
    });
    await page.getByLabel('Markdown text').fill('First delayed save');
    await page.waitForFunction(() => window.__autosaveEntered);
    await page.getByLabel('Markdown text').fill('Newer typing must survive an older response.');
    await app.evaluate(({ BrowserWindow, dialog }) => {
      dialog.showMessageBoxSync = (_window, options) => {
        globalThis.__closePrompt = options;
        return 0;
      };
      BrowserWindow.getAllWindows()[0].close();
    });
    await expect
      .poll(() => app.evaluate(() => globalThis.__closePrompt?.buttons[0]), {
        timeout: 15000,
      })
      .toBe('Keep editing');
    assert.equal((await api(page, '/notebooks')).length, 2);
    // Apps must wait for the in-flight save and its newer queued keystrokes.
    await page.locator('.global-nav button').click();
    await expect(page.locator('.apps-page')).toHaveCount(0);
    await expect(page.getByLabel('Markdown text')).toHaveValue(
      'Newer typing must survive an older response.',
    );
    await page.evaluate(() => window.__releaseAutosave());
    await expect
      .poll(async () => (await api(page, `/notebooks/${notebook.id}/notes`))[0].body, {
        timeout: 20000,
      })
      .toBe('Newer typing must survive an older response.');
    await expect(page.locator('.apps-page')).toBeVisible();
    await page.getByRole('tab', { name: 'Notes', exact: true }).click();
    await page.locator('.note-tabs button').filter({ hasText: saved.title }).click();
    await page.getByRole('button', { name: 'Saved', exact: true }).waitFor();
    assert.equal(
      await page.getByLabel('Markdown text').inputValue(),
      'Newer typing must survive an older response.',
    );
    await page.evaluate(() => window.__restoreFetch());
    const notePath = path.join(data, 'notebooks', notebook.id, 'notes', saved.id + '.md');
    const external = fs.readFileSync(notePath, 'utf8') + '\nExternal change from another editor.';
    fs.writeFileSync(notePath, external);
    await page.getByLabel('Markdown text').fill('Keep this conflict draft across restart.');
    await page
      .locator('.draft-notice')
      .filter({ hasText: 'This note changed outside this editor' })
      .waitFor();
    assert.equal(fs.readFileSync(notePath, 'utf8'), external);
    await page.getByLabel('Markdown text').fill('Keep the latest conflict draft across restart.');
    const draftDir = path.join(data, 'notebooks', notebook.id, 'drafts');
    await expect
      .poll(
        () => {
          const file = fs.readdirSync(draftDir).find((name) => name.endsWith('.json'));
          return file && JSON.parse(fs.readFileSync(path.join(draftDir, file), 'utf8')).note.body;
        },
        { timeout: 15000 },
      )
      .toBe('Keep the latest conflict draft across restart.');
    assert.equal(fs.readFileSync(notePath, 'utf8'), external);
    await capture('02-note-conflict.png');
    await close(true);
    page = await launch();
    await page.getByRole('tab', { name: 'Notes', exact: true }).click();
    await page.locator('.draft-notice').filter({ hasText: 'A draft was recovered' }).waitFor();
    assert.equal(
      await page.getByLabel('Markdown text').inputValue(),
      'Keep the latest conflict draft across restart.',
    );
    await page.getByRole('button', { name: 'Save a copy', exact: true }).click();
    await page.getByRole('button', { name: 'Saved', exact: true }).waitFor();
    assert.equal(fs.readFileSync(notePath, 'utf8'), external);
    assert.equal((await api(page, `/notebooks/${notebook.id}/notes`)).length, 2);
    await page.getByRole('button', { name: 'Separate notebook', exact: true }).click();
    await expect(page.locator('.turn')).toHaveCount(0);
    assert.deepEqual(await api(page, `/notebooks/${empty.id}/chats`), []);
    await page.getByRole('button', { name: 'Settings', exact: true }).click();
    await page.getByLabel('Interface language').selectOption('ru');
    await page.getByRole('button', { name: 'Вернуться', exact: true }).click();
    await page.getByRole('button', { name: 'Persistent research', exact: true }).click();
    await page.getByLabel('История диалогов').waitFor();
    await capture('03-russian-history.png');
    await page.getByRole('tab', { name: ru['nav.research'], exact: true }).click();
    await page.locator('button.research-history').filter({ hasText: research.question }).click();
    await expect(page.getByText(ru['research.interruptedDetail'], { exact: true })).toBeVisible();
    assert.equal(modelCalls, 2, 'Russian recovered Research details must not call a model');
    assert.equal(errors.length, 0, errors.join('\n'));
    fs.writeFileSync(
      path.join(run, 'result.json'),
      JSON.stringify(
        {
          passed: true,
          oldOrigin,
          restartedOrigin: new URL(page.url()).origin,
          modelCalls,
          errors,
          scenarios: [
            'persisted answers and citation snapshots',
            'multiple chats and rename',
            'full service restart',
            'interrupted research recovery and English/Russian details without replay',
            'autosave without Save',
            'workspace navigation preserves an unsavable note and blocks new-notebook creation',
            'late notebook creation response preserves edits made after closing its dialog',
            'workspace navigation waits for the complete in-flight autosave',
            'typing during delayed save',
            'cancel closing while dirty keeps the service alive',
            'external-edit conflict',
            'durable recovered draft and save copy',
            'notebook isolation',
            'Russian controls',
          ],
        },
        null,
        2,
      ),
    );
    console.log(JSON.stringify({ passed: true, artifacts: run }));
  } catch (error) {
    if (app) {
      await capture('failure.png').catch(() => {});
      console.error(
        await app
          .windows()[0]
          ?.locator('body')
          .innerText()
          .catch(() => ''),
      );
    }
    throw error;
  } finally {
    await close(true);
    if (server) {
      server.closeAllConnections();
      await new Promise((resolve) => server.close(resolve));
    }
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
