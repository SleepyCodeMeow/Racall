const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { Readable, Transform } = require('node:stream');
const { pipeline } = require('node:stream/promises');

// Immutable release/candidate inputs. This gate neither rebuilds nor publishes them.
const BASELINE = Object.freeze({
  version: '0.2.0-beta.1',
  source: '70fd79bd69cef06d88c03e1fa5ff88929fc1fa3e',
  name: 'Racall-0.2.0-beta.1-win-x64.exe',
  size: 144616175,
  sha256: '82fc01e779997f7fc4fe5c570cd371c6dc5d83cea0cf7d337b508332f45e02e0',
});
const CANDIDATE = Object.freeze({
  version: '0.3.0-beta.1',
  source: '839d5219d9269071c07e61497061905cc3f707e9',
  run: 40223957296,
  artifact: 12611260738,
  publication: 'approved',
  name: 'Racall-0.3.0-beta.1-win-x64.exe',
  size: 153279432,
  sha256: 'b968cb0f91f0ddfba481853c2949e0978d7d603a9634b18be6d76fde91dc1eb9',
});

function assertHostedWindows(root, env = process.env, host = process) {
  assert.equal(env.CI, 'true', 'Upgrade checks require CI.');
  assert.equal(env.GITHUB_ACTIONS, 'true', 'Upgrade checks require GitHub Actions.');
  assert.equal(env.RUNNER_ENVIRONMENT, 'github-hosted', 'Self-hosted machines are not disposable.');
  assert.equal(env.GITHUB_REPOSITORY, 'SleepyCodeMeow/Racall');
  assert.equal(env.RUNNER_OS, 'Windows');
  assert.equal(env.RUNNER_ARCH, 'X64');
  assert.equal(host.platform, 'win32');
  assert.equal(host.arch, 'x64');
  assert.ok(env.GITHUB_WORKSPACE && path.isAbsolute(env.GITHUB_WORKSPACE));
  assert.equal(path.resolve(env.GITHUB_WORKSPACE), root);
  assert.ok(env.APPDATA && path.isAbsolute(env.APPDATA));
  assert.ok(env.RUNNER_TEMP && path.isAbsolute(env.RUNNER_TEMP));
  assert.ok(env.RACALL_UPGRADE_CANDIDATE_DIR);
  const candidate = path.resolve(env.RACALL_UPGRADE_CANDIDATE_DIR);
  const relative = path.relative(path.resolve(env.RUNNER_TEMP), candidate);
  assert.ok(relative && !relative.startsWith('..') && !path.isAbsolute(relative));
  return { candidate, profile: path.join(env.APPDATA, 'OpenNotebook') };
}

function verifyManifest(manifest) {
  assert.equal(manifest.version, CANDIDATE.version);
  assert.equal(manifest.source, CANDIDATE.source);
  assert.equal(manifest.platform, 'win');
  assert.equal(manifest.arch, 'x64');
  assert.equal(manifest.publication, CANDIDATE.publication);
  assert.deepEqual(manifest.packages, [
    { name: CANDIDATE.name, size: CANDIDATE.size, sha256: CANDIDATE.sha256 },
  ]);
}

async function verifyFile(file, expected) {
  assert.equal(fs.statSync(file).size, expected.size, 'Unexpected installer size.');
  const digest = createHash('sha256');
  for await (const chunk of fs.createReadStream(file)) digest.update(chunk);
  assert.equal(digest.digest('hex'), expected.sha256, 'Unexpected installer SHA-256.');
}

async function prepareInputs(run, candidate) {
  const manifest = JSON.parse(fs.readFileSync(path.join(candidate, 'BUILD.json'), 'utf8'));
  verifyManifest(manifest);
  const next = path.join(candidate, CANDIDATE.name);
  await verifyFile(next, CANDIDATE);
  const sums = fs.readFileSync(path.join(candidate, 'SHA256SUMS.txt'), 'utf8');
  assert.equal(sums.trim(), `${CANDIDATE.sha256}  ${CANDIDATE.name}`);
  const old = path.join(run, BASELINE.name);
  const url = `https://github.com/SleepyCodeMeow/Racall/releases/download/v${BASELINE.version}/${BASELINE.name}`;
  const response = await fetch(url, { signal: AbortSignal.timeout(120000) });
  assert.equal(response.status, 200, 'Published 0.2 installer is unavailable.');
  let bytes = 0;
  const bound = new Transform({
    transform(chunk, _encoding, callback) {
      bytes += chunk.length;
      callback(
        bytes > BASELINE.size ? new Error('Published installer exceeded pinned size.') : null,
        chunk,
      );
    },
  });
  await pipeline(
    Readable.fromWeb(response.body),
    bound,
    fs.createWriteStream(old, { flags: 'wx' }),
  );
  await verifyFile(old, BASELINE);
  return { old, next, manifest };
}

module.exports = { BASELINE, CANDIDATE, assertHostedWindows, verifyManifest, prepareInputs };
