import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const next = spawn(process.execPath, [path.join(root, 'node_modules/next/dist/bin/next'), 'dev', 'apps/web'], { cwd: root, stdio: 'inherit' });
let desktop;
const quit = () => { next.kill(); desktop?.kill(); };
process.on('SIGINT', quit);
process.on('SIGTERM', quit);
for (let n = 0; n < 120; n++) {
  try { if ((await fetch('http://localhost:3000')).ok) break; } catch {}
  if (n === 119) { quit(); throw new Error('Next.js startup timed out'); }
  await new Promise(resolve => setTimeout(resolve, 500));
}
desktop = spawn(process.execPath, [path.join(root, 'node_modules/electron/cli.js'), '.'], {
  cwd: root, stdio: 'inherit', env: { ...process.env, OPENNOTEBOOK_DEV_URL: 'http://localhost:3000' },
});
desktop.on('exit', () => { next.kill(); process.exit(); });
