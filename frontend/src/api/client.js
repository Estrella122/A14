const configuredBase = import.meta.env?.VITE_API_BASE_URL || '/api'
export const apiBaseUrl = configuredBase.replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status, payload = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

function cookieValue(name) {
  return document.cookie.split(';').map((item) => item.trim()).find((item) => item.startsWith(`${name}=`))?.slice(name.length + 1) ?? ''
}

let csrfBootstrap

function responseErrorMessage(response, contentType, payload, text) {
  if (payload?.message) return `HTTP ${response.status}：${payload.message}`
  const normalized = String(text || '').toLowerCase()
  if (response.status === 403 && (normalized.includes('csrf') || normalized.includes('origin checking failed'))) return 'HTTP 403：CSRF 校验失败，请检查前端 Origin 和安全会话'
  if (response.status === 404) return 'HTTP 404：API 不存在或 Vite 代理目标错误'
  if (response.status >= 500) return `HTTP ${response.status}：Django API 内部错误`
  if (!contentType.includes('application/json')) return `HTTP ${response.status}：API 返回了非 JSON 响应（${contentType || '未提供 Content-Type'}）`
  return `请求失败（HTTP ${response.status}）`
}

export async function parseApiResponse(response) {
  const contentType = (response.headers.get('content-type') || '').toLowerCase()
  const text = await response.text()
  let payload = null
  if (contentType.includes('application/json') && text) {
    try { payload = JSON.parse(text) } catch { throw new ApiError(`HTTP ${response.status}：API 返回了无效 JSON`, response.status, { content_type: contentType, body_preview: text.slice(0, 500) }) }
  }
  if (!response.ok || payload?.ok === false) {
    throw new ApiError(responseErrorMessage(response, contentType, payload, text), response.status, {
      response: payload,
      content_type: contentType,
      body_preview: text.slice(0, 500),
    })
  }
  if (!contentType.includes('application/json')) {
    throw new ApiError(`HTTP ${response.status}：API 返回了非 JSON 响应（${contentType || '未提供 Content-Type'}）`, response.status, { content_type: contentType, body_preview: text.slice(0, 500) })
  }
  return payload
}

export async function ensureApiSession() {
  if (!csrfBootstrap) {
    csrfBootstrap = fetch(`${apiBaseUrl}/security/session/`, { credentials: 'same-origin' })
      .then(parseApiResponse)
      .catch((error) => { csrfBootstrap = null; throw error })
  }
  return csrfBootstrap
}

export async function secureFetch(path, options = {}) {
  const method = String(options.method ?? 'GET').toUpperCase()
  const unsafe = !['GET', 'HEAD', 'OPTIONS'].includes(method)
  if (unsafe) await ensureApiSession()
  const csrfToken = unsafe ? decodeURIComponent(cookieValue('csrftoken')) : ''
  return fetch(`${apiBaseUrl}${path}`, {
    credentials: 'same-origin',
    ...options,
    headers: {
      ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
      ...options.headers,
    },
  })
}

export async function apiRequest(path, { signal, body, headers, ...options } = {}) {
  const response = await secureFetch(path, {
    ...options,
    signal,
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  return parseApiResponse(response)
}

export async function apiDownload(path, { signal } = {}) {
  const response = await secureFetch(path, { signal })
  if (!response.ok) {
    let message = `下载失败（HTTP ${response.status}）`
    try {
      const payload = await response.json()
      message = payload.message || message
    } catch {
      // A non-JSON server response still carries the HTTP status above.
    }
    throw new ApiError(message, response.status)
  }
  return {
    blob: await response.blob(),
    disposition: response.headers.get('content-disposition') || '',
  }
}
