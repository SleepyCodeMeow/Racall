#!/usr/bin/env bash
# Prepare locked dependencies for a local development checkout.
set -euo pipefail
cd "$(dirname "$0")/.."
for tool in node npm uv; do
  command -v "$tool" >/dev/null || { printf '%s is required. See CONTRIBUTING.md.\n' "$tool" >&2; exit 1; }
done
node -e 'if (+process.versions.node.split(".")[0] !== 24) { console.error("Use Node.js 24."); process.exit(1); }'
npm ci
uv sync --frozen --python 3.12
printf 'Ready. Run npm run dev to start Racall.\n'
