const configuredBase = import.meta.env.VITE_API_BASE_URL || '/api'
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
export async function ensureApiSession() {
  if (!csrfBootstrap) {
    csrfBootstrap = fetch(`${apiBaseUrl}/security/session/`, { credentials: 'same-origin' })
      .then(async (response) => {
        const payload = await response.json()
        if (!response.ok || payload?.ok === false) throw new ApiError(payload?.message || '安全会话初始化失败', response.status, payload)
        return payload
      })
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

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : await response.text()
  if (!response.ok || payload?.ok === false) {
    const message = payload?.message || `请求失败（HTTP ${response.status}）`
    throw new ApiError(message, response.status, payload)
  }
  return payload
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
