# Native Windows ARM64 prerequisites for the locked cryptography source build.
# Run after setup-node/setup-uv and before `uv sync --frozen` on windows-11-arm.
# No dependency/lock changes, system vcpkg checkout edits, or global Rust default.
# Sources: microsoft/vcpkg tag 2026.10.16; rust-lang/rust tag 1.99.0;
# https://cryptography.io/en/50.0.1/installation/
# https://learn.microsoft.com/visualstudio/ide/reference/command-prompt-powershell
[CmdletBinding()]
param([switch]$DiagnosticsOnly)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $IsWindows -or [Runtime.InteropServices.RuntimeInformation]::OSArchitecture -ne 'Arm64') {
    throw 'This bootstrap requires a native Windows ARM64 runner (windows-11-arm).'
}
if ([Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture -ne 'Arm64') {
    throw 'Use native ARM64 PowerShell; an emulated x64 process cannot certify this build.'
}

function Invoke-Checked([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Executable failed with exit code $LASTEXITCODE." }
}

function Export-BuildEnvironment([string]$Name, [string]$Value) {
    if ($Name -notmatch '^[A-Z][A-Z0-9_]*$' -or $Value -match '[\r\n\x00]') {
        throw 'Invalid single-line build environment value.'
    }
    [Environment]::SetEnvironmentVariable($Name, $Value, 'Process')
    if ($env:GITHUB_ENV) {
        Add-Content -LiteralPath $env:GITHUB_ENV -Value "$Name=$Value" -Encoding utf8
    }
}

function Write-CryptoDiagnostics([string]$Repository) {
    $diagnosticRoot = Join-Path $Repository 'test-results/windows-arm64-crypto'
    New-Item -ItemType Directory -Path $diagnosticRoot -Force | Out-Null
    $logPath = Join-Path $diagnosticRoot 'process.log'
    'Windows ARM64 cryptography build diagnostics (no environment dump)' |
        Set-Content -LiteralPath $logPath -Encoding utf8
    foreach ($tool in @('cl.exe', 'lib.exe', 'link.exe', 'dumpbin.exe', 'rustc.exe')) {
        $command = Get-Command $tool -ErrorAction SilentlyContinue
        $resolvedPath = if ($command) { $command.Source } else { 'not found' }
        "$tool : $resolvedPath" | Tee-Object -FilePath $logPath -Append
    }
    if (-not $env:UV_CACHE_DIR) {
        'UV_CACHE_DIR unavailable; no cryptography build artifacts to inspect.' |
            Tee-Object -FilePath $logPath -Append
        return
    }
    $cryptoRoot = Join-Path $env:UV_CACHE_DIR 'sdists-v9/pypi/cryptography'
    if (-not (Test-Path -LiteralPath $cryptoRoot)) {
        'No source-build directory was retained by uv.' | Tee-Object -FilePath $logPath -Append
        return
    }
    $dumpbin = Get-Command dumpbin.exe -ErrorAction SilentlyContinue
    $artifacts = Get-ChildItem -LiteralPath $cryptoRoot -Recurse -File |
        Where-Object { $_.Name -match '_openssl|^libcryptography_cffi' -and
                       $_.Extension -in @('.obj', '.o', '.lib', '.a', '.rlib', '.c') } |
        Select-Object -First 20
    foreach ($artifact in $artifacts) {
        "Artifact: $($artifact.FullName)" | Tee-Object -FilePath $logPath -Append
        if ($artifact.Extension -eq '.c') {
            Select-String -LiteralPath $artifact.FullName -Pattern 'PyInit__openssl|PyMODINIT_FUNC' -Context 2,2 |
                Out-String -Stream | Tee-Object -FilePath $logPath -Append
        } elseif ($dumpbin) {
            & $dumpbin.Source /headers $artifact.FullName 2>&1 |
                Select-String -Pattern 'machine|File Type|error|warning' |
                Out-String -Stream | Tee-Object -FilePath $logPath -Append
            & $dumpbin.Source /symbols $artifact.FullName 2>&1 |
                Select-String -Pattern 'PyInit|openssl|error|warning' |
                Select-Object -First 50 |
                Out-String -Stream | Tee-Object -FilePath $logPath -Append
        }
    }
    Get-ChildItem -LiteralPath $cryptoRoot -Recurse -File -Filter 'output' |
        Where-Object { $_.FullName -match 'cryptography-cffi' } |
        Select-Object -First 6 | ForEach-Object {
            "Cargo CFFI build output: $($_.FullName)" | Tee-Object -FilePath $logPath -Append
            Get-Content -LiteralPath $_.FullName | Tee-Object -FilePath $logPath -Append
        }
}

$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$buildRoot = Join-Path $repoRoot 'build/arm64'
$vcpkgRoot = Join-Path $buildRoot 'vcpkg'
$vcpkgRevision = '9eec002df1cd109f8f104cd966a763daf9751489'
$rustToolchain = '1.99.0-aarch64-pc-windows-msvc'
$triplet = 'arm64-windows-static-md'
if ($DiagnosticsOnly) {
    Write-CryptoDiagnostics $repoRoot
    exit 0
}
foreach ($tool in @('git', 'node', 'uv', 'rustup')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "$tool is required; use the standard windows-11-arm runner toolchain."
    }
}
$nodeArchitecture = & node -p 'process.arch'
if ($LASTEXITCODE -ne 0 -or $nodeArchitecture.Trim() -ne 'arm64') {
    throw 'setup-node must select native ARM64 Node.js before this bootstrap.'
}

# Select a managed ARM64 interpreter explicitly instead of accepting WoA x64 emulation.
$pythonRequest = 'cpython-3.12-windows-aarch64-none'
Invoke-Checked 'uv' @('python', 'install', $pythonRequest)
$pythonPath = & uv python find $pythonRequest
if ($LASTEXITCODE -ne 0) { throw 'Could not locate the native ARM64 Python interpreter.' }
$pythonPath = $pythonPath.Trim()
Invoke-Checked $pythonPath @('-c', 'import struct, sysconfig; assert struct.calcsize("P") == 8 and sysconfig.get_platform() == "win-arm64", "Expected native ARM64 Python"')
Export-BuildEnvironment 'UV_PYTHON' $pythonPath
Invoke-Checked 'rustup' @('toolchain', 'install', $rustToolchain, '--profile', 'minimal', '--no-self-update')
Export-BuildEnvironment 'RUSTUP_TOOLCHAIN' $rustToolchain
$rustInformation = & rustc -vV
if ($LASTEXITCODE -ne 0 -or $rustInformation -notcontains 'host: aarch64-pc-windows-msvc') {
    throw 'Rust must use the native aarch64-pc-windows-msvc host toolchain.'
}

# Use the runner's installed MSVC. Never install/modify Visual Studio here.
$vswhere = Get-Command vswhere.exe -ErrorAction SilentlyContinue
if ($vswhere) { $vswherePath = $vswhere.Source }
else {
    $vswherePath = @(${env:ProgramFiles(x86)}, $env:ProgramFiles) |
        Where-Object { $_ } |
        ForEach-Object { Join-Path $_ 'Microsoft Visual Studio/Installer/vswhere.exe' } |
        Where-Object { Test-Path -LiteralPath $_ } |
        Select-Object -First 1
}
if (-not $vswherePath) { throw 'The runner is missing Visual Studio Installer/vswhere.exe.' }
$visualStudio = & $vswherePath -latest -prerelease -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.ARM64 -property installationPath
if ($LASTEXITCODE -ne 0 -or -not $visualStudio) { throw 'MSVC ARM64 tools are not installed on this runner.' }
$visualStudio = $visualStudio.Trim()
$developerShell = Join-Path $visualStudio 'Common7/Tools/Launch-VsDevShell.ps1'
if (-not (Test-Path -LiteralPath $developerShell)) { throw 'Visual Studio Developer PowerShell is missing.' }
$previousPaths = @($env:PATH -split ';')
# An amd64-hosted compiler can run under Windows-on-Arm; its target is explicitly ARM64.
& $developerShell -Arch arm64 -HostArch amd64 -SkipAutomaticLocation
if ($env:VSCMD_ARG_TGT_ARCH -ne 'arm64') { throw 'MSVC did not activate the ARM64 target.' }
foreach ($tool in @('cl.exe', 'link.exe', 'nmake.exe')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "MSVC tool missing: $tool" }
}
# cc-rs may use PATH when a Developer Shell is detected. Bind the ARM64-target
# compiler/archive/linker explicitly so GITHUB_PATH ordering cannot change them.
$msvcBin = Join-Path $env:VCToolsInstallDir 'bin/Hostx64/arm64'
$armCompiler = Join-Path $msvcBin 'cl.exe'
$armArchiver = Join-Path $msvcBin 'lib.exe'
$armLinker = Join-Path $msvcBin 'link.exe'
$armDumpbin = Join-Path $msvcBin 'dumpbin.exe'
foreach ($toolPath in @($armCompiler, $armArchiver, $armLinker, $armDumpbin)) {
    if (-not (Test-Path -LiteralPath $toolPath)) { throw "ARM64-target MSVC tool missing: $toolPath" }
}
New-Item -ItemType Directory -Path $buildRoot -Force | Out-Null
$probeSource = Join-Path $buildRoot 'compiler-probe.c'
$probeObject = Join-Path $buildRoot 'compiler-probe.obj'
'__declspec(dllexport) void *PyInit__openssl(void) { return (void *)0; }' |
    Set-Content -LiteralPath $probeSource -Encoding ascii
Invoke-Checked $armCompiler @('/nologo', '/c', '/GL-', "/Fo$probeObject", $probeSource)
$probeBytes = [IO.File]::ReadAllBytes($probeObject)
if ($probeBytes.Length -lt 20 -or [BitConverter]::ToUInt16($probeBytes, 0) -ne 0xAA64) {
    throw 'The selected C compiler did not generate an ARM64 COFF object.'
}
$probeSymbols = & $armDumpbin /symbols $probeObject
if ($LASTEXITCODE -ne 0 -or -not ($probeSymbols -match '\|\s+PyInit__openssl\s*$')) {
    throw 'The ARM64 C probe did not expose the expected CFFI-compatible C symbol.'
}
Write-Output "ARM64 C compiler: $armCompiler"
Write-Output "ARM64 archive tool: $armArchiver"
Write-Output "ARM64 target linker: $armLinker"
Write-Output 'C probe passed: COFF machine AA64; external symbol PyInit__openssl.'
# Persist only build-tool variables, never a complete environment dump.
foreach ($name in @('INCLUDE', 'LIB', 'LIBPATH', 'VCINSTALLDIR', 'VSINSTALLDIR',
                    'VCToolsInstallDir', 'VCToolsVersion', 'WindowsSdkDir', 'WindowsSDKVersion',
                    'WindowsLibPath', 'UniversalCRTSdkDir', 'UCRTVersion',
                    'VSCMD_ARG_HOST_ARCH', 'VSCMD_ARG_TGT_ARCH', 'VisualStudioVersion')) {
    $value = [Environment]::GetEnvironmentVariable($name, 'Process')
    if ($value) { Export-BuildEnvironment $name.ToUpperInvariant() $value }
}
if ($env:GITHUB_PATH) {
    foreach ($entry in @($env:PATH -split ';' | Where-Object { $_ -and $_ -notin $previousPaths })) {
        if ($entry -match '[\r\n\x00]') { throw 'Invalid MSVC tool path.' }
        Add-Content -LiteralPath $env:GITHUB_PATH -Value $entry -Encoding utf8
    }
}

# Pin the port registry as well as vcpkg's bootstrap metadata, separately from C:\vcpkg.
New-Item -ItemType Directory -Path $buildRoot -Force | Out-Null
if (-not (Test-Path -LiteralPath $vcpkgRoot)) {
    Invoke-Checked 'git' @('init', $vcpkgRoot)
    Invoke-Checked 'git' @('-C', $vcpkgRoot, 'remote', 'add', 'origin', 'https://github.com/microsoft/vcpkg.git')
    Invoke-Checked 'git' @('-C', $vcpkgRoot, 'config', 'core.longpaths', 'true')
    Invoke-Checked 'git' @('-C', $vcpkgRoot, 'fetch', '--depth=1', 'origin', $vcpkgRevision)
    Invoke-Checked 'git' @('-C', $vcpkgRoot, 'checkout', '--detach', $vcpkgRevision)
}
if (-not (Test-Path -LiteralPath (Join-Path $vcpkgRoot '.git'))) {
    throw 'The private vcpkg build directory exists but is not the expected checkout.'
}
$actualRevision = & git -C $vcpkgRoot rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $actualRevision.Trim() -ne $vcpkgRevision) {
    throw 'The private vcpkg checkout does not match the pinned revision; refusing to reset it.'
}
$sourceChanges = & git -C $vcpkgRoot status --porcelain --untracked-files=no
if ($LASTEXITCODE -ne 0 -or $sourceChanges) { throw 'Pinned vcpkg sources contain local changes.' }
$port = Get-Content -LiteralPath (Join-Path $vcpkgRoot 'ports/openssl/vcpkg.json') -Raw | ConvertFrom-Json
if ($port.version -ne '3.6.5' -or $port.'port-version' -ne 2) { throw 'Unexpected pinned OpenSSL port.' }
Export-BuildEnvironment 'VCPKG_ROOT' $vcpkgRoot
Export-BuildEnvironment 'VCPKG_VISUAL_STUDIO_PATH' $visualStudio
Export-BuildEnvironment 'VCPKG_DISABLE_METRICS' '1'
Export-BuildEnvironment 'VCPKG_MAX_CONCURRENCY' '2'
$vcpkgExecutable = Join-Path $vcpkgRoot 'vcpkg.exe'
if (-not (Test-Path -LiteralPath $vcpkgExecutable)) {
    Invoke-Checked (Join-Path $vcpkgRoot 'bootstrap-vcpkg.bat') @('-disableMetrics')
}
Push-Location $vcpkgRoot
try {
    Invoke-Checked $vcpkgExecutable @('install', "openssl:$triplet", '--host-triplet=arm64-windows', '--disable-metrics')
} finally { Pop-Location }
$opensslRoot = Join-Path $vcpkgRoot "installed/$triplet"
foreach ($artifact in @('include/openssl/opensslv.h', 'lib/libcrypto.lib', 'lib/libssl.lib', 'share/openssl/copyright')) {
    if (-not (Test-Path -LiteralPath (Join-Path $opensslRoot $artifact))) {
        throw "The static ARM64 OpenSSL build is incomplete: $artifact"
    }
}
Export-BuildEnvironment 'OPENSSL_DIR' $opensslRoot
Export-BuildEnvironment 'OPENSSL_LIB_DIR' (Join-Path $opensslRoot 'lib')
Export-BuildEnvironment 'OPENSSL_INCLUDE_DIR' (Join-Path $opensslRoot 'include')
Export-BuildEnvironment 'OPENSSL_STATIC' '1'
Export-BuildEnvironment 'OPENSSL_NO_VENDOR' '1'
Export-BuildEnvironment 'RACALL_OPENSSL_NOTICE' (Join-Path $opensslRoot 'share/openssl/copyright')
Export-BuildEnvironment 'CC' $armCompiler
Export-BuildEnvironment 'AR' $armArchiver
Export-BuildEnvironment 'CC_AARCH64_PC_WINDOWS_MSVC' $armCompiler
Export-BuildEnvironment 'AR_AARCH64_PC_WINDOWS_MSVC' $armArchiver
Export-BuildEnvironment 'CARGO_TARGET_AARCH64_PC_WINDOWS_MSVC_LINKER' $armLinker
Export-BuildEnvironment 'CC_ENABLE_DEBUG_OUTPUT' '1'
Export-BuildEnvironment 'CARGO_BUILD_TARGET' 'aarch64-pc-windows-msvc'
Export-BuildEnvironment 'CARGO_BUILD_JOBS' '2'
Export-BuildEnvironment 'UV_NO_BINARY_PACKAGE' 'cryptography'
Write-Output 'ARM64 prerequisites ready: Python 3.12, Rust 1.99.0, pinned OpenSSL 3.6.5#2 (static/MD).'
Write-Output 'Next: uv sync --frozen; cryptography remains at the exact version/hash in uv.lock.'
