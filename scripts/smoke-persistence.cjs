const { _electron: electron, expect } = require("@playwright/test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const root = path.resolve(__dirname, "..");
const run = path.join(root, "test-results", "persistence-" + Date.now());
const data = path.join(run, "data");
fs.mkdirSync(data, { recursive: true });
const errors = [];
let app, server;
async function launch() {
  const env = {
    ...process.env,
    OPENNOTEBOOK_DATA_DIR: data,
    OPENNOTEBOOK_SMOKE_MODE: "1",
  };
  delete env.ELECTRON_RUN_AS_NODE;
  app = await electron.launch({
    ...(process.env.OPENNOTEBOOK_TEST_EXE
      ? {
          executablePath: process.env.OPENNOTEBOOK_TEST_EXE,
          args: ["--disable-gpu"],
        }
      : { args: [root, "--disable-gpu"] }),
    env,
    timeout: 60000,
  });
  const page = await app.firstWindow({ timeout: 60000 });
  page.on("pageerror", (e) => errors.push(e.message));
  // Electron handles beforeunload with a native dialog; CDP cannot dismiss it.
  page.on("dialog", async dialog => {
    if (dialog.type() !== "beforeunload") await dialog.dismiss();
  });
  await app.evaluate(({ BrowserWindow }) =>
    BrowserWindow.getAllWindows()[0].webContents.setBackgroundThrottling(false),
  );
  await page.locator(".navigation").waitFor();
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
async function api(page, endpoint, method = "GET", body) {
  return page.evaluate(
    async ({ endpoint, method, body }) => {
      const response = await fetch("/api" + endpoint, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });
      if (!response.ok)
        throw new Error(
          "HTTP " + response.status + ": " + (await response.text()),
        );
      return response.json();
    },
    { endpoint, method, body },
  );
}
async function capture(name) {
  const encoded = await app.evaluate(async ({ BrowserWindow }) =>
    (
      await BrowserWindow.getAllWindows()[0].webContents.capturePage(
        undefined,
        { stayHidden: true, stayAwake: true },
      )
    )
      .toPNG()
      .toString("base64"),
  );
  fs.writeFileSync(path.join(run, name), Buffer.from(encoded, "base64"));
}
(async () => {
  try {
    let modelCalls = 0;
    server = http.createServer((request, response) => {
      let text = "";
      request.on("data", (chunk) => (text += chunk));
      request.on("end", () => {
        try {
          modelCalls++;
          const payload = JSON.parse(text);
          const input = JSON.parse(payload.messages[1].content);
          const result = input.claims
            ? { supported_indices: [0] }
            : {
                claims: [
                  {
                    text: "Marigold launches on October 18.",
                    evidence_ids: [
                      input.evidence.find((e) => e.quote.includes("October 18"))
                        .id,
                    ],
                  },
                ],
                message: "",
              };
          response.writeHead(200, { "Content-Type": "application/json" });
          response.end(
            JSON.stringify({
              choices: [{ message: { content: JSON.stringify(result) } }],
            }),
          );
        } catch (e) {
          response.writeHead(500);
          response.end(String(e));
        }
      });
    });
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    let page = await launch();
    const notebook = await api(page, "/notebooks", "POST", {
      title: "Persistent research",
    });
    const empty = await api(page, "/notebooks", "POST", {
      title: "Separate notebook",
    });
    await api(page, "/settings", "PUT", {
      base_url: `http://127.0.0.1:${server.address().port}/v1`,
      model: "deterministic-test",
      embedding_model: "",
    });
    const source = await page.evaluate(async (id) => {
      const form = new FormData();
      form.append(
        "file",
        new Blob(["# Marigold\n\nMarigold launches on October 18."]),
        "mission.md",
      );
      return (
        await fetch(`/api/notebooks/${id}/sources`, {
          method: "POST",
          body: form,
        })
      ).json();
    }, notebook.id);
    await expect
      .poll(
        async () =>
          (await api(page, `/notebooks/${notebook.id}/sources/${source.id}`))
            .source.status,
      )
      .toBe("ready");
    await page.reload();
    await page
      .getByLabel("Question about your materials")
      .fill("When does Marigold launch?");
    await page
      .getByRole("button", { name: "Send question", exact: true })
      .click();
    await page
      .locator(".answer-body")
      .getByText("Marigold launches on October 18.", { exact: false })
      .waitFor();
    await expect(
      page.getByRole("button", { name: "Rename", exact: true }),
    ).toBeEnabled();
    await page.getByRole("button", { name: "Rename", exact: true }).click();
    await page.getByLabel("Chat name").fill("Mission questions");
    await page
      .locator(".chat-rename")
      .getByRole("button", { name: "Save", exact: true })
      .click();
    const firstThread = (await api(page, `/notebooks/${notebook.id}/chats`))[0]
      .id;
    await page.getByRole("button", { name: "New chat", exact: true }).click();
    await expect(
      page.getByLabel("Question about your materials"),
    ).toBeEnabled();
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await page.getByLabel("Question about your materials").fill("Marigold");
    await page
      .getByRole("button", { name: "Send question", exact: true })
      .click();
    await page.locator(".search-results button").first().waitFor();
    const oldOrigin = new URL(page.url()).origin;
    await close();
    page = await launch();
    await page.getByLabel("Chat history").selectOption(firstThread);
    await page
      .locator(".answer-body")
      .getByText("Marigold launches on October 18.", { exact: false })
      .waitFor();
    await page.locator(".citation-buttons button").first().click();
    await page.locator("mark").filter({ hasText: "October 18" }).waitFor();
    assert.equal(modelCalls, 2, "Restart must not call the model again");
    await capture("01-restored-chat.png");
    await page
      .getByRole("button", { name: "Close source", exact: true })
      .click();
    await page.getByRole("tab", { name: "Notes", exact: true }).click();
    await page.getByRole("button", { name: "Create", exact: true }).click();
    await page.getByLabel("Note title").fill("Daily note");
    await page
      .getByLabel("Markdown text")
      .fill("Autosaved without pressing Save. [[Next step]]");
    await page.getByRole("button", { name: "Saved", exact: true }).waitFor();
    const saved = (await api(page, `/notebooks/${notebook.id}/notes`))[0];
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
        if (!used && String(args[0]).endsWith("/notes/autosave")) {
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
    await page.getByLabel("Markdown text").fill("First delayed save");
    await page.waitForFunction(() => window.__autosaveEntered);
    await page
      .getByLabel("Markdown text")
      .fill("Newer typing must survive an older response.");
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
      .toBe("Keep editing");
    assert.equal((await api(page, "/notebooks")).length, 2);
    await page.evaluate(() => window.__releaseAutosave());
    await expect
      .poll(
        async () =>
          (await api(page, `/notebooks/${notebook.id}/notes`))[0].body,
        { timeout: 20000 },
      )
      .toBe("Newer typing must survive an older response.");
    await page.getByRole("button", { name: "Saved", exact: true }).waitFor();
    assert.equal(
      await page.getByLabel("Markdown text").inputValue(),
      "Newer typing must survive an older response.",
    );
    await page.evaluate(() => window.__restoreFetch());
    const notePath = path.join(
      data,
      "notebooks",
      notebook.id,
      "notes",
      saved.id + ".md",
    );
    const external =
      fs.readFileSync(notePath, "utf8") +
      "\nExternal change from another editor.";
    fs.writeFileSync(notePath, external);
    await page
      .getByLabel("Markdown text")
      .fill("Keep this conflict draft across restart.");
    await page
      .locator(".draft-notice")
      .filter({ hasText: "This note changed outside this editor" })
      .waitFor();
    assert.equal(fs.readFileSync(notePath, "utf8"), external);
    await page
      .getByLabel("Markdown text")
      .fill("Keep the latest conflict draft across restart.");
    const draftDir = path.join(data, "notebooks", notebook.id, "drafts");
    await expect
      .poll(
        () => {
          const file = fs
            .readdirSync(draftDir)
            .find((name) => name.endsWith(".json"));
          return (
            file &&
            JSON.parse(fs.readFileSync(path.join(draftDir, file), "utf8")).note
              .body
          );
        },
        { timeout: 15000 },
      )
      .toBe("Keep the latest conflict draft across restart.");
    assert.equal(fs.readFileSync(notePath, "utf8"), external);
    await capture("02-note-conflict.png");
    await close(true);
    page = await launch();
    await page.getByRole("tab", { name: "Notes", exact: true }).click();
    await page
      .locator(".draft-notice")
      .filter({ hasText: "A draft was recovered" })
      .waitFor();
    assert.equal(
      await page.getByLabel("Markdown text").inputValue(),
      "Keep the latest conflict draft across restart.",
    );
    await page
      .getByRole("button", { name: "Save a copy", exact: true })
      .click();
    await page.getByRole("button", { name: "Saved", exact: true }).waitFor();
    assert.equal(fs.readFileSync(notePath, "utf8"), external);
    assert.equal(
      (await api(page, `/notebooks/${notebook.id}/notes`)).length,
      2,
    );
    await page
      .getByRole("button", { name: "Separate notebook", exact: true })
      .click();
    await expect(page.locator(".turn")).toHaveCount(0);
    assert.deepEqual(await api(page, `/notebooks/${empty.id}/chats`), []);
    await page.getByRole("button", { name: "Settings", exact: true }).click();
    await page.getByLabel("Interface language").selectOption("ru");
    await page.getByRole("button", { name: "Вернуться", exact: true }).click();
    await page
      .getByRole("button", { name: "Persistent research", exact: true })
      .click();
    await page.getByLabel("История диалогов").waitFor();
    await capture("03-russian-history.png");
    assert.equal(errors.length, 0, errors.join("\n"));
    fs.writeFileSync(
      path.join(run, "result.json"),
      JSON.stringify(
        {
          passed: true,
          oldOrigin,
          restartedOrigin: new URL(page.url()).origin,
          modelCalls,
          errors,
          scenarios: [
            "persisted answers and citation snapshots",
            "multiple chats and rename",
            "full service restart",
            "autosave without Save",
            "typing during delayed save",
            "cancel closing while dirty keeps the service alive",
            "external-edit conflict",
            "durable recovered draft and save copy",
            "notebook isolation",
            "Russian controls",
          ],
        },
        null,
        2,
      ),
    );
    console.log(JSON.stringify({ passed: true, artifacts: run }));
  } catch (error) {
    if (app) {
      await capture("failure.png").catch(() => {});
      console.error(
        await app
          .windows()[0]
          ?.locator("body")
          .innerText()
          .catch(() => ""),
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
