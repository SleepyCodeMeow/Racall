const assert = require('node:assert/strict');
const path = require('node:path');
const { test } = require('node:test');
const { Arch, getArchSuffix, getArtifactArchName } = require('builder-util');
const { target, nativeTarget, packagedLayout, packagedExecutable, resourcesForExecutable,
  distributionFiles } = require('./native-target.cjs');

const root = path.resolve('fixture-project');
const version = '0.3.0-beta.1';
const cases = [
  ['win32', 'x64', 'win-unpacked', 'win-x64.exe'],
  ['win32', 'arm64', 'win-arm64-unpacked', 'win-arm64.exe'],
  ['darwin', 'x64', 'mac', 'mac-x64.dmg'],
  ['darwin', 'arm64', 'mac-arm64', 'mac-arm64.dmg'],
  ['linux', 'x64', 'linux-unpacked', 'linux-amd64.deb'],
  ['linux', 'arm64', 'linux-arm64-unpacked', 'linux-arm64.deb'],
];

for (const [platform, arch, directory, installer] of cases) {
  test(`${platform}/${arch} matches native builder output and distribution naming`, () => {
    const selected = target(platform, arch);
    const layout = packagedLayout(root, selected);
    const builderDirectory = selected.builderPlatform + getArchSuffix(Arch[arch]) + (platform === 'darwin' ? '' : '-unpacked');
    assert.equal(path.basename(layout.unpacked), directory);
    assert.equal(directory, builderDirectory, 'Match installed electron-builder architecture convention');
    const files = distributionFiles(root, version, selected);
    assert.equal(Object.values(files)[0], path.join(root, 'release', `Racall-${version}-${installer}`));
    assert.ok(layout.executables.every(file => file.startsWith(layout.unpacked + path.sep)));
    assert.equal(resourcesForExecutable(layout.executables[0], selected), layout.resources);
    if (platform === 'linux') {
      assert.equal(files.appImage, path.join(root, 'release', `Racall-${version}-linux-${getArtifactArchName(Arch[arch], 'AppImage')}.AppImage`));
      assert.equal(files.deb, path.join(root, 'release', `Racall-${version}-linux-${getArtifactArchName(Arch[arch], 'deb')}.deb`));
    }
    assert.equal(nativeTarget({ RACALL_TARGET_ARCH: arch, RACALL_TARGET_PLATFORM: selected.builderPlatform }, { platform, arch }).arch, arch);
  });
}

test('an ARM64 check cannot silently select an existing x64 build', () => {
  const arm = packagedLayout(root, target('linux', 'arm64'));
  const x64 = packagedLayout(root, target('linux', 'x64'));
  assert.throws(() => packagedExecutable(arm, file => x64.executables.includes(file)), /linux-arm64-unpacked/);
  assert.equal(packagedExecutable(arm, file => file === arm.executables[1]), arm.executables[1]);
});

test('native checks reject architecture emulation and unsupported platforms before installation', () => {
  assert.throws(() => nativeTarget({ RACALL_TARGET_ARCH: 'arm64' }, { platform: 'win32', arch: 'x64' }), /running x64/);
  assert.throws(() => nativeTarget({ RACALL_TARGET_PLATFORM: 'mac' }, { platform: 'linux', arch: 'arm64' }), /running linux/);
  for (const arch of ['ia32', 'armv7l', 'universal', 'amd64', '']) assert.throws(() => target('linux', arch), /Unsupported/);
  assert.throws(() => target('freebsd', 'x64'), /Unsupported/);
  assert.throws(() => distributionFiles(root, '../outside', target('linux', 'x64')), /Invalid/);
  assert.throws(() => distributionFiles(root, undefined, target('linux', 'x64')), /Invalid/);
});
