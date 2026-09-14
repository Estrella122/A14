import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

const isWindows = process.platform === 'win32'
const npmCommand = isWindows ? 'npm.cmd' : 'npm'
const venvPython = isWindows ? join('.venv', 'Scripts', 'python.exe') : join('.venv', 'bin', 'python')

function probePython(command) {
  if (command.includes('/') && !existsSync(command)) return false
  const result = spawnSync(command, ['-c', 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'])
  return result.status === 0
}

function run(command, args) {
  const result = spawnSync(command, args, { cwd: process.cwd(), stdio: 'inherit' })
  if (result.status !== 0) process.exit(result.status || 1)
}

const bundledPython = join(homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3')
const candidates = [
  process.env.PROCESSPILOT_BOOTSTRAP_PYTHON,
  'python3.14',
  'python3.13',
  'python3.12',
  'python3',
  'python',
  ...(isWindows ? ['py'] : []),
  bundledPython,
].filter(Boolean)
const python = candidates.find(probePython)

if (!python) {
  console.error('[ProcessPilot] 未找到 Python 3.12+。请安装后执行：PROCESSPILOT_BOOTSTRAP_PYTHON=/path/to/python3 npm run setup')
  process.exit(1)
}

console.log(`[ProcessPilot] 使用 ${python} 创建本地运行环境…`)
run(python, ['-m', 'venv', '--clear', '.venv'])
run(venvPython, ['-m', 'pip', 'install', '--upgrade', 'pip'])
run(venvPython, ['-m', 'pip', 'install', '-r', 'requirements.txt'])
run(npmCommand, ['--prefix', 'frontend', 'ci'])
run(venvPython, ['manage.py', 'check'])
run(venvPython, ['manage.py', 'migrate', '--noinput'])
run(venvPython, ['manage.py', 'seed_knowledge_base'])
console.log('[ProcessPilot] 环境安装完成。现在可以执行 npm run dev。')
