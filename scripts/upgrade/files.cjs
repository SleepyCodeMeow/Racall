const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');

function writeEvidence(run, name, value) {
  fs.writeFileSync(path.join(run, name), JSON.stringify(value, null, 2) + '\n');
}

function portableSnapshot(data) {
  const result = {};
  function visit(directory) {
    for (const entry of fs
      .readdirSync(directory, { withFileTypes: true })
      .sort((a, b) => a.name.localeCompare(b.name))) {
      const file = path.join(directory, entry.name);
      assert.equal(entry.isSymbolicLink(), false, 'Fixture data must not traverse links.');
      if (entry.isDirectory()) visit(file);
      else {
        const relative = path.relative(data, file).split(path.sep).join('/');
        // The retrieval database is rebuildable. Audit/backend logs intentionally grow.
        if (/^(?:index\.sqlite3(?:-wal|-shm|-journal)?|audit\.jsonl|backend\.log)$/.test(relative))
          continue;
        const bytes = fs.readFileSync(file);
        result[relative] = {
          size: bytes.length,
          sha256: createHash('sha256').update(bytes).digest('hex'),
        };
      }
    }
  }
  visit(data);
  return result;
}

function compareSnapshots(before, after) {
  assert.ok(Object.keys(before).length > 0, 'An empty profile cannot prove preservation.');
  for (const [file, expected] of Object.entries(before)) {
    assert.deepEqual(after[file], expected, `Authoritative data changed or disappeared: ${file}`);
  }
}

function assertPreserved(before, data) {
  const after = portableSnapshot(data);
  compareSnapshots(before, after);
  return after;
}

module.exports = { writeEvidence, portableSnapshot, compareSnapshots, assertPreserved };
