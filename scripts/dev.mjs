import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { join } from 'node:path'

const children = new Set()
let shuttingDown = false
const isWindows = process.platform === 'win32'
const npmCommand = isWindows ? 'npm.cmd' : 'npm'
const defaultPython = isWindows ? join('.venv', 'Scripts', 'python.exe') : join('.venv', 'bin', 'python')
const python = process.env.PROCESSPILOT_PYTHON || defaultPython
const host = process.env.PROCESSPILOT_HOST || '127.0.0.1'

if (!existsSync(python)) {
  console.error('[ProcessPilot] Python运行环境不存在，请先执行 npm run setup。')
  process.exit(1)
}

function run(command, args) {
  const child = spawn(command, args, {
    cwd: process.cwd(),
    env: process.env,
    stdio: 'inherit',
  })
  children.add(child)
  child.once('exit', () => children.delete(child))
  return child
}

function waitForExit(child) {
  return new Promise((resolve, reject) => {
    if (child.exitCode !== null) {
      if (child.exitCode === 0) resolve()
      else reject(new Error(`进程退出：${child.exitCode}`))
      return
    }
    if (child.signalCode) {
      reject(new Error(`进程退出：${child.signalCode}`))
      return
    }
    child.once('error', reject)
    child.once('exit', (code, signal) => {
      if (code === 0) resolve()
      else reject(new Error(`进程退出：${signal || code}`))
    })
  })
}

const pause = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds))

async function probe(url, validate) {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(700) })
    const text = await response.text()
    return {
      reachable: true,
      valid: response.ok && validate(text),
      status: response.status,
    }
  } catch {
    return { reachable: false, valid: false, status: null }
  }
}

async function waitForService(url, validate, child, label) {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    const result = await probe(url, validate)
    if (result.valid) return
    if (child.exitCode !== null || child.signalCode) {
      throw new Error(`${label}启动失败，请查看上方日志`)
    }
    await pause(120)
  }
  throw new Error(`${label}启动超时`)
}

function shutdown(signal = 'SIGTERM') {
  if (shuttingDown) return
  shuttingDown = true
  for (const child of children) {
    if (!child.killed) child.kill(signal)
  }
}

process.on('SIGINT', () => shutdown('SIGINT'))
process.on('SIGTERM', () => shutdown('SIGTERM'))
process.on('exit', () => shutdown('SIGTERM'))

try {
  console.log('\n[ProcessPilot] 正在检查数据库迁移…')
  await waitForExit(run(python, ['-c', 'import django, pandas, numpy, rapidfuzz, pandera, matplotlib']))
  await waitForExit(run(python, ['manage.py', 'migrate', '--noinput']))
  await waitForExit(run(python, ['manage.py', 'seed_knowledge_base']))

  const managedServices = []
  const backendUrl = 'http://127.0.0.1:8000/api/'
  const frontendUrl = 'http://127.0.0.1:5176/overview/'
  const backendValidator = (text) => {
    try {
      const payload = JSON.parse(text)
      return payload.ok === true && payload.workflows?.closed_loop_optimization
    } catch {
      return false
    }
  }
  const frontendValidator = (text) => text.includes('id="app"') && text.includes('APC Agent 工作台')

  const existingBackend = await probe(backendUrl, backendValidator)
  if (existingBackend.reachable && !existingBackend.valid) {
    throw new Error('8000 端口已被其他程序占用，请先关闭该程序')
  }
  if (existingBackend.valid) {
    console.log('\n[ProcessPilot] 已检测到可用的闭环寻优后端，直接复用：http://127.0.0.1:8000')
  } else {
    console.log('\n[ProcessPilot] 正在启动闭环寻优后端：http://127.0.0.1:8000')
    const backend = run(python, ['manage.py', 'runserver', `${host}:8000`])
    managedServices.push({ name: '后端', child: backend })
    await waitForService(backendUrl, backendValidator, backend, '闭环寻优后端')
  }

  const existingFrontend = await probe(frontendUrl, frontendValidator)
  if (existingFrontend.reachable && !existingFrontend.valid) {
    throw new Error('5176 端口已被其他程序占用，请先关闭该程序')
  }
  if (existingFrontend.valid) {
    console.log('[ProcessPilot] 已检测到可用的前端，直接复用：http://127.0.0.1:5176/overview/')
  } else {
    console.log('[ProcessPilot] 正在启动前端：http://127.0.0.1:5176/overview/')
    const frontend = run(npmCommand, ['--prefix', 'frontend', 'run', 'dev', '--', '--host', host, '--port', '5176', '--strictPort'])
    managedServices.push({ name: '前端', child: frontend })
    await waitForService(frontendUrl, frontendValidator, frontend, '前端')
  }

  console.log('\n[ProcessPilot] 前后端已连接完成，请打开：http://127.0.0.1:5176/closed-loop-optimization/')
  if (managedServices.length) {
    const exitResult = await Promise.race(
      managedServices.map(({ name, child }) => waitForExit(child).then(() => name)),
    )
    if (!shuttingDown) throw new Error(`${exitResult}服务意外停止`)
  } else {
    console.log('[ProcessPilot] 两项服务此前已经运行，无需重复启动。')
  }
} catch (error) {
  if (!shuttingDown) {
    console.error(`\n[ProcessPilot] 启动失败：${error.message}`)
    process.exitCode = 1
  }
} finally {
  shutdown()
}
