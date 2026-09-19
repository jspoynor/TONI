#!/usr/bin/env node
// Launches the Nemo backend (backend/app.py) from its venv for `npm run dev`.
// Only fills in DATABASE_URL/NEMO_STORAGE/CORS_ORIGINS when the shell hasn't
// already set them, so a real Postgres setup (see backend/README.md) is left
// alone — this is purely a "just works" default for local SQLite dev.
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const backendDir = path.join(repoRoot, 'backend')
const venvPython = path.join(
  backendDir,
  '.venv',
  process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
)

if (!existsSync(venvPython)) {
  console.error(
    `[backend] No venv found at ${venvPython}.\n` +
      '[backend] Run the one-time setup first (see backend/README.md):\n' +
      '[backend]   cd backend && python -m venv .venv && ' +
      '.venv/Scripts/activate && pip install -r requirements.txt',
  )
  process.exit(1)
}

const sqliteUrl = `sqlite:///${path.join(backendDir, 'nemo.db').replace(/\\/g, '/')}`

const env = {
  ...process.env,
  DATABASE_URL: process.env.DATABASE_URL ?? sqliteUrl,
  NEMO_STORAGE: process.env.NEMO_STORAGE ?? path.join(backendDir, 'storage'),
  CORS_ORIGINS:
    process.env.CORS_ORIGINS ??
    'http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173',
}

console.log(`[backend] DATABASE_URL=${env.DATABASE_URL}`)
console.log(`[backend] NEMO_STORAGE=${env.NEMO_STORAGE}`)

const child = spawn(
  venvPython,
  ['-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '8010'],
  { cwd: backendDir, env, stdio: 'inherit' },
)

child.on('exit', (code, signal) => {
  process.exit(signal ? 1 : (code ?? 0))
})

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => child.kill(signal))
}
