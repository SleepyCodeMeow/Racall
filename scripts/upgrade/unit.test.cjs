// Pure host/input/preservation checks. Never invoke an installer or Electron.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { BASELINE, CANDIDATE, assertHostedWindows, verifyManifest } = require('./inputs.cjs');
const { compareSnapshots } = require('./files.cjs');

const root = path.resolve('fixture-workspace');
const temp = path.resolve('fixture-runner-temp');
const env = {
  CI: 'true',
  GITHUB_ACTIONS: 'true',
  RUNNER_ENVIRONMENT: 'github-hosted',
  GITHUB_REPOSITORY: 'SleepyCodeMeow/Racall',
  RUNNER_OS: 'Windows',
  RUNNER_ARCH: 'X64',
  GITHUB_WORKSPACE: root,
  RUNNER_TEMP: temp,
  APPDATA: path.resolve('fixture-appdata'),
  RACALL_UPGRADE_CANDIDATE_DIR: path.join(temp, 'candidate'),
};
const host = { platform: 'win32', arch: 'x64' };

test('installation guards reject local, self-hosted, wrong-architecture and escaped paths', () => {
  assert.ok(assertHostedWindows(root, env, host).profile.endsWith('OpenNotebook'));
  for (const key of [
    'CI',
    'GITHUB_ACTIONS',
    'RUNNER_ENVIRONMENT',
    'GITHUB_REPOSITORY',
    'RUNNER_OS',
    'RUNNER_ARCH',
    'GITHUB_WORKSPACE',
    'RUNNER_TEMP',
    'APPDATA',
    'RACALL_UPGRADE_CANDIDATE_DIR',
  ]) {
    assert.throws(() => assertHostedWindows(root, { ...env, [key]: '' }, host), key);
  }
  assert.throws(() =>
    assertHostedWindows(root, { ...env, RUNNER_ENVIRONMENT: 'self-hosted' }, host),
  );
  assert.throws(() => assertHostedWindows(root, env, { ...host, arch: 'arm64' }));
  assert.throws(() =>
    assertHostedWindows(root, { ...env, RACALL_UPGRADE_CANDIDATE_DIR: root }, host),
  );
});

test('the candidate manifest cannot substitute another source, package or released state', () => {
  const manifest = {
    version: CANDIDATE.version,
    source: CANDIDATE.source,
    platform: 'win',
    arch: 'x64',
    publication: CANDIDATE.publication,
    packages: [{ name: CANDIDATE.name, size: CANDIDATE.size, sha256: CANDIDATE.sha256 }],
  };
  verifyManifest(manifest);
  assert.throws(() =>
    verifyManifest({
      ...manifest,
      publication: CANDIDATE.publication === 'approved' ? 'hold' : 'approved',
    }),
  );
  for (const key of ['version', 'source', 'platform', 'arch', 'publication'])
    assert.throws(() => verifyManifest({ ...manifest, [key]: 'other' }));
  assert.throws(() =>
    verifyManifest({
      ...manifest,
      packages: [{ ...manifest.packages[0], sha256: BASELINE.sha256 }],
    }),
  );
  assert.throws(() =>
    verifyManifest({ ...manifest, packages: [...manifest.packages, manifest.packages[0]] }),
  );
});

test('preservation permits new records but rejects lost or modified old files', () => {
  const before = { 'notes/old.md': { size: 4, sha256: 'old-hash' } };
  compareSnapshots(before, { ...before, 'materials/new.json': { size: 10, sha256: 'new-hash' } });
  assert.throws(() => compareSnapshots(before, {}));
  assert.throws(() => compareSnapshots(before, { 'notes/old.md': { size: 4, sha256: 'changed' } }));
  assert.throws(() => compareSnapshots({}, {}));
});
