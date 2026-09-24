const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
let executable, resources;
if (process.platform === 'win32') {
  executable = path.join(root, 'release/win-unpacked/Racall.exe');
  resources = path.join(root, 'release/win-unpacked/resources');
} else if (process.platform === 'darwin') {
  const bundle = path.join(root, 'release', process.arch === 'arm64' ? 'mac-arm64' : 'mac', 'Racall.app/Contents');
  executable = path.join(bundle, 'MacOS/Racall');
  resources = path.join(bundle, 'Resources');
} else {
  const unpacked = path.join(root, 'release/linux-unpacked');
  executable = ['racall', 'Racall', 'open-notebook-desktop'].map(name => path.join(unpacked, name)).find(file => fs.existsSync(file));
  resources = path.join(unpacked, 'resources');
}
if (!executable || !fs.existsSync(executable)) throw new Error('Packaged executable is missing. Build installers first.');
const env = { ...process.env, OPENNOTEBOOK_TEST_EXE: executable,
  RACALL_BACKEND_BINARY: path.join(resources, 'backend', process.platform === 'win32' ? 'open-notebook-api.exe' : 'open-notebook-api') };
function run(command, args) {
  const result = spawnSync(command, args, { cwd: root, env, stdio: 'inherit', windowsHide: true });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status || 1);
}
run(process.execPath, ['scripts/smoke-desktop.cjs']);
run(process.execPath, ['scripts/smoke-languages.cjs']);
run('uv', ['run', 'python', 'scripts/check_bundle.py']);
