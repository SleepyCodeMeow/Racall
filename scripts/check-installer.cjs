// Runs only on disposable CI hosts: exercise actual install/copy and uninstall paths.
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
if (process.env.CI !== "true")
  throw new Error("Installer checks require a disposable CI host.");
const root = path.resolve(__dirname, "..");
const version = require("../package.json").version;
const run = path.join(root, "test-results", "installer-" + Date.now());
assert.ok(run.startsWith(root + path.sep));
fs.mkdirSync(run, { recursive: true });
function command(file, args, options = {}) {
  const result = spawnSync(file, args, {
    cwd: root,
    encoding: "utf8",
    windowsHide: true,
    timeout: 240000,
    ...options,
  });
  if (result.error || result.status !== 0)
    throw new Error(
      `${file} failed (${result.status}): ${result.error || ""}\n${(result.stderr || result.stdout || "").slice(-5000)}`,
    );
  return result.stdout.trim();
}
function check(executable) {
  assert.ok(fs.existsSync(executable), executable);
  const result = spawnSync(
    process.execPath,
    ["scripts/smoke-maintenance.cjs"],
    {
      cwd: root,
      env: { ...process.env, OPENNOTEBOOK_TEST_EXE: executable },
      windowsHide: true,
      stdio: "inherit",
      timeout: 240000,
    },
  );
  if (result.error || result.status !== 0)
    throw new Error("Installed application did not pass maintenance smoke.");
}
const appData =
  process.platform === "win32"
    ? process.env.APPDATA
    : process.platform === "darwin"
      ? path.join(os.homedir(), "Library", "Application Support")
      : process.env.XDG_CONFIG_HOME || path.join(os.homedir(), ".config");
const sentinel = path.join(
  appData,
  "OpenNotebook",
  "knowledge",
  "installer-check-sentinel.txt",
);
fs.mkdirSync(path.dirname(sentinel), { recursive: true });
fs.writeFileSync(sentinel, "User knowledge must survive uninstall.", {
  flag: "wx",
});
const checks = [];
if (process.platform === "win32") {
  const installer = path.join(root, "release", `Racall-${version}-win-x64.exe`);
  const destination = path.join(run, "installed");
  command(installer, ["/S", "/D=" + destination], {
    windowsVerbatimArguments: true,
  });
  const executable = path.join(destination, "Racall.exe");
  check(executable);
  checks.push("NSIS silent installation and installed app");
  const uninstaller = fs
    .readdirSync(destination)
    .find((name) => /^Uninstall.*\.exe$/i.test(name));
  assert.ok(uninstaller, "Uninstaller missing");
  command(path.join(destination, uninstaller), ["/S", "_?=" + destination], {
    windowsVerbatimArguments: true,
  });
  assert.equal(
    fs.existsSync(executable),
    false,
    "Uninstaller left the app executable",
  );
  checks.push("NSIS uninstall preserves user knowledge");
} else if (process.platform === "darwin") {
  const dmg = path.join(
    root,
    "release",
    `Racall-${version}-mac-${process.arch}.dmg`,
  );
  const mount = path.join(run, "mounted");
  fs.mkdirSync(mount);
  command("hdiutil", [
    "attach",
    dmg,
    "-nobrowse",
    "-readonly",
    "-mountpoint",
    mount,
  ]);
  const bundle = path.join(run, "Applications", "Racall.app");
  try {
    command("ditto", [path.join(mount, "Racall.app"), bundle]);
  } finally {
    command("hdiutil", ["detach", mount]);
  }
  check(path.join(bundle, "Contents", "MacOS", "Racall"));
  checks.push("DMG mount, application copy and installed app");
} else {
  const deb = path.join(root, "release", `Racall-${version}-linux-amd64.deb`);
  const name = command("dpkg-deb", ["--field", deb, "Package"]);
  assert.match(name, /^[a-z0-9][a-z0-9+.-]+$/);
  command("sudo", ["apt-get", "update"]);
  command("sudo", ["apt-get", "install", "-y", "--no-install-recommends", deb]);
  try {
    const files = command("dpkg", ["--listfiles", name]).split("\n");
    const executable = files.find(
      (file) =>
        file.startsWith("/opt/") &&
        ["racall", "Racall", "open-notebook-desktop"].includes(
          path.basename(file),
        ) &&
        fs.statSync(file).isFile(),
    );
    assert.ok(executable, "Installed Debian executable missing");
    check(executable);
    checks.push("Debian package installation and installed app");
  } finally {
    command("sudo", ["dpkg", "--remove", name]);
  }
  checks.push("Debian removal preserves user knowledge");
  const appImage = path.join(
    root,
    "release",
    `Racall-${version}-linux-x86_64.AppImage`,
  );
  command(appImage, ["--appimage-extract"], { cwd: run });
  check(path.join(run, "squashfs-root", "AppRun"));
  checks.push("AppImage extracted application (FUSE mounting not exercised)");
}
assert.equal(
  fs.readFileSync(sentinel, "utf8"),
  "User knowledge must survive uninstall.",
);
fs.writeFileSync(
  path.join(run, "result.json"),
  JSON.stringify({ passed: true, platform: process.platform, checks }, null, 2),
);
console.log(JSON.stringify({ passed: true, checks, artifacts: run }));
