import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { join } from 'node:path'

const defaultPython = process.platform === 'win32'
  ? join('.venv', 'Scripts', 'python.exe')
  : join('.venv', 'bin', 'python')
const python = process.env.PROCESSPILOT_PYTHON || defaultPython

if (!existsSync(python)) {
  console.error('[ProcessPilot] Python运行环境不存在，请先执行 npm run setup。')
  process.exit(1)
}

const result = spawnSync(python, process.argv.slice(2), {
  cwd: process.cwd(),
  env: process.env,
  stdio: 'inherit',
})
process.exit(result.status ?? 1)
