import test from 'node:test'
import assert from 'node:assert/strict'
import { ApiError, parseApiResponse } from '../src/api/client.js'

function response(status, contentType, body) {
  return {
    status,
    ok: status >= 200 && status < 300,
    headers: { get: (name) => name.toLowerCase() === 'content-type' ? contentType : null },
    text: async () => body,
  }
}

test('HTML CSRF response preserves HTTP 403 and gives a useful error', async () => {
  await assert.rejects(
    parseApiResponse(response(403, 'text/html; charset=utf-8', '<!DOCTYPE html><p>CSRF verification failed. Origin checking failed</p>')),
    (error) => error instanceof ApiError && error.status === 403 && error.message.includes('CSRF 校验失败') && error.payload.body_preview.startsWith('<!DOCTYPE'),
  )
})

test('missing HTML API preserves HTTP 404 instead of throwing JSON syntax error', async () => {
  await assert.rejects(
    parseApiResponse(response(404, 'text/html', '<!DOCTYPE html><title>Not Found</title>')),
    (error) => error instanceof ApiError && error.status === 404 && error.message.includes('API 不存在'),
  )
})

test('valid JSON remains unchanged', async () => {
  const payload = await parseApiResponse(response(200, 'application/json', '{"ok":true,"data":{"id":1}}'))
  assert.deepEqual(payload.data, { id: 1 })
})

test('JSON API errors retain both status and backend reason', async () => {
  await assert.rejects(
    parseApiResponse(response(404, 'application/json', '{"ok":false,"message":"未知 API 表名"}')),
    (error) => error.status === 404 && error.message === 'HTTP 404：未知 API 表名',
  )
})
