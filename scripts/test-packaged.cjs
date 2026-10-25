const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const {
  nativeTarget,
  packagedLayout,
  packagedExecutable,
  resourcesForExecutable,
} = require('./native-target.cjs');
const root = path.resolve(__dirname, '..');
const target = nativeTarget();
let executable, resources;
if (process.env.OPENNOTEBOOK_TEST_EXE) {
  executable = path.resolve(process.env.OPENNOTEBOOK_TEST_EXE);
  resources = resourcesForExecutable(executable, target);
} else {
  const layout = packagedLayout(root, target);
  executable = packagedExecutable(layout);
  resources = layout.resources;
}
if (!executable || !fs.existsSync(executable))
  throw new Error('Packaged executable is missing. Build installers first.');
const env = {
  ...process.env,
  OPENNOTEBOOK_TEST_EXE: executable,
  RACALL_BACKEND_BINARY: path.join(
    resources,
    'backend',
    process.platform === 'win32' ? 'open-notebook-api.exe' : 'open-notebook-api',
  ),
};
function run(command, args) {
  const result = spawnSync(command, args, { cwd: root, env, stdio: 'inherit', windowsHide: true });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status || 1);
}
run('uv', [
  'run',
  'python',
  'scripts/check_native_arch.py',
  '--binary',
  executable,
  '--binary',
  env.RACALL_BACKEND_BINARY,
]);
run(process.execPath, ['scripts/smoke-desktop.cjs']);
run(process.execPath, ['scripts/smoke-languages.cjs']);
run(process.execPath, ['scripts/smoke-providers.cjs']);
run(process.execPath, ['scripts/smoke-workbench.cjs']);
run(process.execPath, ['scripts/smoke-studio.cjs']);
run(process.execPath, ['scripts/smoke-persistence.cjs']);
run(process.execPath, ['scripts/smoke-maintenance.cjs']);
run('uv', ['run', 'python', 'scripts/check_bundle.py']);
run('uv', ['run', 'python', 'scripts/check_provider_bundle.py']);
