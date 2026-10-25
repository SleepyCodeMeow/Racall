/** Native Electron package locations, shared by the packaged and installer checks. */
const fs = require('node:fs');
const path = require('node:path');

const platforms = { win32: 'win', darwin: 'mac', linux: 'linux' };

function target(platform, arch) {
  if (!Object.hasOwn(platforms, platform) || !['x64', 'arm64'].includes(arch)) {
    throw new Error(`Unsupported native target: ${platform}/${arch}`);
  }
  return { platform, arch, builderPlatform: platforms[platform] };
}

function nativeTarget(
  env = process.env,
  host = { platform: process.platform, arch: process.arch },
) {
  const result = target(host.platform, host.arch);
  if (env.RACALL_TARGET_ARCH && env.RACALL_TARGET_ARCH !== result.arch) {
    throw new Error(
      `Native checks require ${env.RACALL_TARGET_ARCH} Node.js; running ${result.arch}`,
    );
  }
  if (env.RACALL_TARGET_PLATFORM && env.RACALL_TARGET_PLATFORM !== result.builderPlatform) {
    throw new Error(
      `Native checks require ${env.RACALL_TARGET_PLATFORM}; running ${result.builderPlatform}`,
    );
  }
  return result;
}

function packagedLayout(root, value) {
  const { platform, arch, builderPlatform } = target(value.platform, value.arch);
  // electron-builder 26: defaultArch is x64 on every native platform.
  const directory =
    builderPlatform + (arch === 'x64' ? '' : '-arm64') + (platform === 'darwin' ? '' : '-unpacked');
  const unpacked = path.join(root, 'release', directory);
  if (platform === 'darwin') {
    const contents = path.join(unpacked, 'Racall.app', 'Contents');
    return {
      unpacked,
      resources: path.join(contents, 'Resources'),
      executables: [path.join(contents, 'MacOS', 'Racall')],
    };
  }
  return {
    unpacked,
    resources: path.join(unpacked, 'resources'),
    executables: (platform === 'win32'
      ? ['Racall.exe']
      : ['racall', 'Racall', 'open-notebook-desktop']
    ).map((name) => path.join(unpacked, name)),
  };
}

function packagedExecutable(layout, exists = fs.existsSync) {
  const executable = layout.executables.find((file) => exists(file));
  if (!executable)
    throw new Error(
      `Packaged executable is missing in ${layout.unpacked}. Build this native target first.`,
    );
  return executable;
}

function resourcesForExecutable(executable, value) {
  const { platform } = target(value.platform, value.arch);
  return path.resolve(
    path.dirname(executable),
    platform === 'darwin' ? '../Resources' : 'resources',
  );
}

function distributionFiles(root, version, value) {
  const { platform, arch } = target(value.platform, value.arch);
  if (typeof version !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9.+-]*$/.test(version))
    throw new Error('Invalid package version');
  const prefix = path.join(root, 'release', `Racall-${version}-`);
  if (platform === 'win32') return { installer: `${prefix}win-${arch}.exe` };
  if (platform === 'darwin')
    return { dmg: `${prefix}mac-${arch}.dmg`, zip: `${prefix}mac-${arch}.zip` };
  return {
    deb: `${prefix}linux-${arch === 'x64' ? 'amd64' : 'arm64'}.deb`,
    appImage: `${prefix}linux-${arch === 'x64' ? 'x86_64' : 'arm64'}.AppImage`,
  };
}

module.exports = {
  target,
  nativeTarget,
  packagedLayout,
  packagedExecutable,
  resourcesForExecutable,
  distributionFiles,
};
