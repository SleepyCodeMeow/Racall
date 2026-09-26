const { _electron: electron, expect } = require("@playwright/test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const run = path.join(root, "test-results", "maintenance-" + Date.now());
const data = path.join(run, "data");
fs.mkdirSync(data, { recursive: true });
let app;
const errors = [];
async function launch() {
  const env = {
    ...process.env,
    OPENNOTEBOOK_DATA_DIR: data,
    OPENNOTEBOOK_SMOKE_MODE: "1",
  };
  delete env.ELECTRON_RUN_AS_NODE;
  app = await electron.launch({
    ...(env.OPENNOTEBOOK_TEST_EXE
      ? { executablePath: env.OPENNOTEBOOK_TEST_EXE, args: ["--disable-gpu"] }
      : { args: [root, "--disable-gpu"] }),
    env,
    timeout: 60000,
  });
  const page = await app.firstWindow({ timeout: 60000 });
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("dialog", async (d) => {
    if (d.type() !== "beforeunload") await d.dismiss();
  });
  await app.evaluate(({ BrowserWindow }) =>
    BrowserWindow.getAllWindows()[0].webContents.setBackgroundThrottling(false),
  );
  await page.locator(".navigation").waitFor();
  return page;
}
async function close() {
  if (!app) return;
  const previous = app;
  app = undefined;
  await previous.evaluate(({ BrowserWindow }) =>
    BrowserWindow.getAllWindows().forEach((w) => w.destroy()),
  );
  await previous.close();
}
async function api(page, endpoint, method = "GET", body) {
  return page.evaluate(
    async ({ endpoint, method, body }) => {
      const r = await fetch("/api" + endpoint, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    },
    { endpoint, method, body },
  );
}
async function capture(name) {
  const png = await app.evaluate(async ({ BrowserWindow }) =>
    (
      await BrowserWindow.getAllWindows()[0].webContents.capturePage(
        undefined,
        { stayHidden: true, stayAwake: true },
      )
    )
      .toPNG()
      .toString("base64"),
  );
  fs.writeFileSync(path.join(run, name), Buffer.from(png, "base64"));
}
(async () => {
  try {
    let page = await launch();
    const notebook = await api(page, "/notebooks", "POST", {
      title: "Release research",
    });
    const prefix = `/notebooks/${notebook.id}`;
    const source = await page.evaluate(
      async ({ prefix }) => {
        const form = new FormData();
        form.append(
          "file",
          new Blob(["# Mission\n\nMarigold launches on October 18."], {
            type: "text/markdown",
          }),
          "mission.md",
        );
        const r = await fetch("/api" + prefix + "/sources", {
          method: "POST",
          body: form,
        });
        if (!r.ok) throw new Error(await r.text());
        return r.json();
      },
      { prefix },
    );
    await expect
      .poll(async () => (await api(page, prefix + "/sources"))[0].status, {
        timeout: 30000,
      })
      .toBe("ready");
    await page.reload();
    await page.locator(".navigation").waitFor();
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await page
      .getByLabel("Question about your materials")
      .fill("Marigold launches");
    await page
      .getByRole("button", { name: "Send question", exact: true })
      .click();
    await page.locator(".search-results button").first().waitFor();
    await page.locator(".search-results button").first().click();
    await expect(page.locator("mark")).toContainText("October 18");
    await page
      .getByLabel("Replacement file")
      .setInputFiles({
        name: "mission-update.md",
        mimeType: "text/markdown",
        buffer: Buffer.from("# Mission\n\nMarigold launches on November 22."),
      });
    await expect
      .poll(async () => (await api(page, prefix + "/sources"))[0].version, {
        timeout: 30000,
      })
      .not.toBe(source.version);
    const newer = (await api(page, prefix + "/sources"))[0];
    await expect(page.locator(".detail-panel .draft-notice")).toContainText(
      "Previous version",
    );
    await expect(page.locator("mark")).toContainText("October 18");
    await expect(
      page.getByLabel("Source version").locator("option"),
    ).toHaveCount(2);
    await page.getByLabel("Source version").selectOption(newer.version);
    await expect(page.locator(".source-content")).toContainText("November 22");
    await page.getByLabel("Source version").selectOption(source.version);
    await expect(page.locator("mark")).toContainText("October 18");
    const originalResponse = page.waitForResponse((r) =>
      r.url().endsWith(`/versions/${source.version}/original`),
    );
    await page
      .getByRole("button", { name: "Open original", exact: true })
      .click();
    const download = page.getByRole("link", {
      name: "Download file",
      exact: true,
    });
    await download.waitFor();
    assert.ok((await download.getAttribute("href")).startsWith("blob:"));
    const returned = await originalResponse;
    assert.equal(returned.status(), 200);
    const oldFile = await page.evaluate(async endpoint => {
      const response = await fetch("/api" + endpoint);
      if (!response.ok) throw new Error("Original returned " + response.status);
      return response.text();
    }, `${prefix}/sources/${source.id}/versions/${source.version}/original`);
    assert.ok(oldFile.includes("October 18"));
    await capture("01-historical-source.png");
    await page
      .getByLabel("Replacement file")
      .setInputFiles({
        name: "broken.pdf",
        mimeType: "application/pdf",
        buffer: Buffer.from("not a PDF"),
      });
    await expect(page.locator(".detail-title .source-error")).toContainText(
      "previous working version",
      { timeout: 30000 },
    );
    assert.equal(
      (await api(page, prefix + "/sources"))[0].version,
      newer.version,
    );
    await page
      .getByRole("button", { name: "Close source", exact: true })
      .click();
    await page.getByRole("tab", { name: "Notes", exact: true }).click();
    await page.getByRole("button", { name: "Create", exact: true }).click();
    await page.getByLabel("Note title").fill("Keep my notes");
    await page.getByLabel("Markdown text").fill("Survives trash and restore.");
    await page.getByRole("button", { name: "Saved", exact: true }).waitFor();
    await page
      .getByRole("button", { name: "Manage Release research", exact: true })
      .click();
    await page
      .getByRole("dialog")
      .getByLabel("Name", { exact: true })
      .fill("Renamed research");
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Save", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Manage Renamed research", exact: true })
      .click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Move to trash", exact: true })
      .click();
    await page
      .getByRole("dialog", { name: "Move notebook to trash?", exact: true })
      .waitFor();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Move to trash", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Renamed research", exact: true }),
    ).toHaveCount(0);
    assert.deepEqual(await api(page, "/notebooks"), []);
    await page
      .getByRole("button", { name: "Notebook trash", exact: true })
      .click();
    await page
      .getByRole("dialog")
      .getByText("Renamed research", { exact: true })
      .waitFor();
    await capture("02-notebook-trash.png");
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Restore", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Renamed research", exact: true })
      .waitFor();
    assert.equal(
      (await api(page, prefix + "/notes"))[0].body,
      "Survives trash and restore.",
    );
    assert.equal(
      (await api(page, prefix + "/sources"))[0].version,
      newer.version,
    );
    await close();
    page = await launch();
    await page
      .getByRole("button", { name: "Renamed research", exact: true })
      .waitFor();
    await page.locator(".search-results button").first().click();
    await expect(page.locator("mark")).toContainText("October 18");
    assert.equal(errors.length, 0, errors.join("\n"));
    fs.writeFileSync(
      path.join(run, "result.json"),
      JSON.stringify(
        {
          passed: true,
          errors,
          scenarios: [
            "versioned file replacement",
            "historical citation and original",
            "failed update retains working source",
            "notebook rename",
            "trash confirmation and restore",
            "notes and chats survive restart",
          ],
        },
        null,
        2,
      ),
    );
    console.log(JSON.stringify({ passed: true, artifacts: run }));
  } catch (e) {
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
    throw e;
  } finally {
    await close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
