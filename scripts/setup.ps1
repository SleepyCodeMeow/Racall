# Prepare locked dependencies for a local development checkout.
$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot '..')
try {
    foreach ($tool in @('node', 'npm', 'uv')) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "$tool is required. See CONTRIBUTING.md." }
    }
    $nodeVersion = node -p process.versions.node
    if ($LASTEXITCODE -ne 0 -or $nodeVersion.Split('.')[0] -ne '24') { throw 'Use Node.js 24.' }
    npm ci
    if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }
    uv sync --frozen --python 3.12
    if ($LASTEXITCODE -ne 0) { throw 'uv sync failed.' }
    Write-Output 'Ready. Run npm run dev to start Racall.'
} finally { Pop-Location }
