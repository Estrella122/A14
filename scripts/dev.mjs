import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { join } from 'node:path'

const children = new Set()
let shuttingDown = false
const isWindows = process.platform === 'win32'
const npmCommand = isWindows ? 'npm.cmd' : 'npm'
const defaultPython = isWindows ? join('.venv', 'Scripts', 'python.exe') : join('.venv', 'bin', 'python')
const python = process.env.PROCESSPILOT_PYTHON || defaultPython
const host = process.env.PROCESSPILOT_HOST || '127.0.0.1'
const pythonIsExplicitPath = python.includes('/') || python.includes('\\')

function portFromEnv(name, fallback) {
  const raw = process.env[name] || String(fallback)
  const port = Number(raw)
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    console.error(`[ProcessPilot] ${name} 必须是 1-65535 之间的整数，当前值：${raw}`)
    process.exit(1)
  }
  return port
}

const backendPort = portFromEnv('PROCESSPILOT_BACKEND_PORT', 8000)
const mcpPort = portFromEnv('PROCESSPILOT_MCP_PORT', 8010)
const frontendPort = portFromEnv('PROCESSPILOT_FRONTEND_PORT', 5176)
const backendOrigin = `http://127.0.0.1:${backendPort}`
const backendUrl = `${backendOrigin}/api/`
const mcpUrl = `http://127.0.0.1:${mcpPort}/mcp`
const frontendOrigin = `http://127.0.0.1:${frontendPort}`
const frontendUrl = `${frontendOrigin}/overview/`

// CI commonly supplies "python" as a PATH-resolved command. existsSync only
// applies to filesystem paths and incorrectly rejected that valid setup.
if (pythonIsExplicitPath && !existsSync(python)) {
  console.error('[ProcessPilot] Python运行环境不存在，请先执行 npm run setup。')
  process.exit(1)
}

function run(command, args, extraEnv = {}) {
  const child = spawn(command, args, {
    cwd: process.cwd(),
    env: { ...process.env, ...extraEnv },
    stdio: 'inherit',
  })
  children.add(child)
  child.once('exit', () => children.delete(child))
  return child
}

function mcpReady(url) {
  return spawnSync(python, ['scripts/check_mcp.py', url], {
    cwd: process.cwd(),
    env: process.env,
    stdio: 'ignore',
    timeout: 4000,
  }).status === 0
}

async function waitForMcp(url, child) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    if (mcpReady(url)) return
    if (child.exitCode !== null || child.signalCode) throw new Error('MCP Server启动失败，请查看上方日志')
    await pause(150)
  }
  throw new Error('MCP Server启动超时')
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

// The launcher owns its children. Translate terminal Ctrl+C into SIGTERM so
// Python services can finish their normal shutdown path without stack traces.
process.on('SIGINT', () => shutdown('SIGTERM'))
process.on('SIGTERM', () => shutdown('SIGTERM'))
process.on('exit', () => shutdown('SIGTERM'))

try {
  console.log('\n[ProcessPilot] 正在检查数据库迁移…')
  await waitForExit(run(python, ['-c', 'import django, pandas, numpy, rapidfuzz, pandera, matplotlib']))
  await waitForExit(run(python, ['manage.py', 'migrate', '--noinput']))
  await waitForExit(run(python, ['manage.py', 'seed_knowledge_base']))

  const managedServices = []
  const backendValidator = (text) => {
    try {
      const payload = JSON.parse(text)
      return payload.ok === true && payload.workflows?.closed_loop_optimization && payload.mcp?.enabled === true
    } catch {
      return false
    }
  }
  const frontendValidator = (text) => text.includes('id="app"') && text.includes('APC Agent 工作台')

  const existingBackend = await probe(backendUrl, backendValidator)
  if (existingBackend.reachable && !existingBackend.valid) {
    throw new Error(`${backendPort} 端口已被其他程序占用，请先关闭该程序或设置 PROCESSPILOT_BACKEND_PORT`)
  }
  if (existingBackend.valid) {
    console.log(`\n[ProcessPilot] 已检测到可用的闭环寻优后端，直接复用：${backendOrigin}`)
  } else {
    console.log(`\n[ProcessPilot] 正在启动闭环寻优后端：${backendOrigin}`)
    const backend = run(python, ['manage.py', 'runserver', `${host}:${backendPort}`, '--noreload'], {
      PROCESSPILOT_INLINE_WORKER: 'false',
      PROCESSPILOT_MCP_URL: mcpUrl,
    })
    managedServices.push({ name: '后端', child: backend })
    await waitForService(backendUrl, backendValidator, backend, '闭环寻优后端')
  }

  if (mcpReady(mcpUrl)) {
    console.log(`[ProcessPilot] 已检测到可用的 MCP Server，直接复用：${mcpUrl}`)
  } else {
    const occupied = await probe(mcpUrl, () => true)
    if (occupied.reachable) throw new Error(`${mcpPort} 端口已被非 ProcessPilot MCP 服务占用，请先关闭该程序或设置 PROCESSPILOT_MCP_PORT`)
    console.log(`[ProcessPilot] 正在启动 MCP Server：${mcpUrl}`)
    const mcpServer = run(python, ['scripts/mcp_server.py'], {
      PROCESSPILOT_MCP_TRANSPORT: 'streamable-http',
      PROCESSPILOT_MCP_HOST: '127.0.0.1',
      PROCESSPILOT_MCP_PORT: String(mcpPort),
      PROCESSPILOT_INLINE_WORKER: 'true',
    })
    managedServices.push({ name: 'MCP Server', child: mcpServer })
    await waitForMcp(mcpUrl, mcpServer)
  }

  console.log('[ProcessPilot] 正在启动 Runtime Worker')
  const worker = run(python, ['manage.py', 'run_runtime_worker'], {
    PROCESSPILOT_INLINE_WORKER: 'false',
    PROCESSPILOT_MCP_URL: mcpUrl,
  })
  managedServices.push({ name: 'Runtime Worker', child: worker })

  const existingFrontend = await probe(frontendUrl, frontendValidator)
  if (existingFrontend.reachable && !existingFrontend.valid) {
    throw new Error(`${frontendPort} 端口已被其他程序占用，请先关闭该程序或设置 PROCESSPILOT_FRONTEND_PORT`)
  }
  if (existingFrontend.valid) {
    console.log(`[ProcessPilot] 已检测到可用的前端，直接复用：${frontendUrl}`)
  } else {
    console.log(`[ProcessPilot] 正在启动前端：${frontendUrl}`)
    const frontend = run(
      npmCommand,
      ['--prefix', 'frontend', 'run', 'dev', '--', '--host', host, '--port', String(frontendPort), '--strictPort'],
      { VITE_API_PROXY_TARGET: backendOrigin },
    )
    managedServices.push({ name: '前端', child: frontend })
    await waitForService(frontendUrl, frontendValidator, frontend, '前端')
  }

  console.log(`\n[ProcessPilot] 前端、后端、MCP 与 Worker 已连接完成，请打开：${frontendOrigin}/closed-loop-optimization/`)
  if (managedServices.length) {
    const exitResult = await Promise.race(
      managedServices.map(({ name, child }) => waitForExit(child).then(() => name)),
    )
    if (!shuttingDown) throw new Error(`${exitResult}服务意外停止`)
  } else {
    console.log('[ProcessPilot] 服务此前已经运行，无需重复启动。')
  }
} catch (error) {
  if (!shuttingDown) {
    console.error(`\n[ProcessPilot] 启动失败：${error.message}`)
    process.exitCode = 1
  }
} finally {
  shutdown()
}
