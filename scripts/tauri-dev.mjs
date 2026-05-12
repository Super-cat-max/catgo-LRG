#!/usr/bin/env node
// Wrapper for the `tauri` CLI that aligns devUrl with the vite desktop
// dev-server port computed from the worktree offset.
//
// When invoked with subcommand `dev`, we inject `--config` so tauri.conf.json's
// devUrl matches the port Vite will actually listen on. For other subcommands
// (build, icon, info, ...) we just pass arguments through untouched.
//
// Both this script and vite.shared.ts::worktree_offset() MUST implement the
// same hash algorithm, otherwise Tauri will poll the wrong port.

import { spawn } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

function worktree_offset() {
  const dir = resolve('.')
  const match = dir.match(/\.(?:claude[/\\])?worktrees[/\\]([^/\\]+)/)
  if (!match) return 0
  let hash = 0
  for (const ch of match[1]) hash = ((hash << 5) - hash + ch.charCodeAt(0)) | 0
  return 1 + (Math.abs(hash) % 99)
}

const args = process.argv.slice(2)
const subcommand = args[0]
const extra_env = {}
let final_args = args

if (subcommand === 'dev') {
  const offset = worktree_offset()
  const desktop_port = process.env.PORT ? parseInt(process.env.PORT, 10) : 3100 + offset
  const dev_url = `http://localhost:${desktop_port}`
  // Drop externalBin in dev: beforeDevCommand starts the Python backend
  // separately (pnpm desktop:serve), so Tauri doesn't need a sidecar exe to exist.
  const config_override = JSON.stringify({
    build: { devUrl: dev_url },
    bundle: { externalBin: [] },
  })

  // Write to a temp file so Windows cmd.exe doesn't strip the JSON's quotes
  // when spawn runs with shell: true. Tauri's --config accepts a file path.
  const config_path = join(tmpdir(), `catgo-tauri-dev-${process.pid}.json`)
  writeFileSync(config_path, config_override)

  console.log(`[tauri-dev] worktree offset=${offset}, devUrl=${dev_url}`)

  // Ensure Vite picks the same port via process.env.PORT
  extra_env.PORT = String(desktop_port)

  // Insert --config right after `dev`; user's original args follow.
  final_args = ['dev', '--config', config_path, ...args.slice(1)]
}

const child = spawn('tauri', final_args, {
  stdio: 'inherit',
  shell: process.platform === 'win32',
  env: { ...process.env, ...extra_env },
})

child.on('exit', (code, signal) => {
  if (signal) process.kill(process.pid, signal)
  else process.exit(code ?? 0)
})
