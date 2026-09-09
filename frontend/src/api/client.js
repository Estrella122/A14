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

export async function apiRequest(path, { signal, body, headers, ...options } = {}) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
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
  const response = await fetch(`${apiBaseUrl}${path}`, { signal })
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
