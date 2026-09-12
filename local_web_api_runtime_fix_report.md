# 本地 Web API 运行时修复报告

## 结论

真实故障是 Django CSRF Origin 校验拒绝了来自 `http://127.0.0.1:5176` 的 POST。浏览器已先通过 `/api/security/session/` 获取 CSRF cookie，并正确携带 `X-CSRFToken`；但 Django 未配置 `CSRF_TRUSTED_ORIGINS`，中间件在 view 之前就返回 HTML 403。CSV 上传再无条件调用 `response.json()`，从而把真实 403 二次掩盖为 `Unexpected token '<'`。

## 运行版本与进程

- 验证前 Git commit：`7682f40dac2cbc8076b062cc03a0f02eeb6913af`，与 `origin/main` 一致。
- Django：`127.0.0.1:8000`，进程工作目录 `/Users/komi/Documents/ChatGPT/作品修复/A14`。
- Vite：`127.0.0.1:5176`，进程工作目录 `/Users/komi/Documents/ChatGPT/作品修复/A14/frontend`。
- Django 日志证明 `/api/agent/chat/live/`、`/api/pipeline/runs/` 已到达当前 Django 进程，不是旧 checkout、旧 backend 或 Vite index.html fallback。
- 未发现 Service Worker 注册。

## 修复前真实 HTTP

### Agent Live

- URL：`http://127.0.0.1:5176/api/agent/chat/live/`
- Method：POST
- Status：403 Forbidden
- Content-Type：`text/html; charset=utf-8`
- Body 开头：`<!DOCTYPE html>`
- Django 原因：`Origin checking failed - http://127.0.0.1:5176 does not match any trusted origins.`

### CSV 上传

- URL：`http://127.0.0.1:5176/api/pipeline/runs/`
- Method：POST multipart/form-data
- Status：403 Forbidden
- Content-Type：`text/html; charset=utf-8`
- Body 开头：`<!DOCTYPE html>`
- 拒绝发生在 CSRF middleware，早于 CSV 读取、字段统一和任何工业算法，因此与 CSV 格式无关。

## CSRF、CORS 与 Vite Proxy

- `CsrfViewMiddleware` 正常启用，没有全局关闭或增加 `csrf_exempt`。
- 前端 `secureFetch()` 正确设置 `credentials: same-origin`，也携带 CSRF cookie 与 `X-CSRFToken`。
- Vite 实际配置为 `/api → http://127.0.0.1:8000`，聊天 POST、CSV POST 和 Skill Run GET 都走同一 `/api` base URL。
- 请求已到达 Django，因此不是 Vite proxy 路径或端口故障。
- 这是同源 Vite proxy 开发模式，不需要额外全局 CORS 放开；真实拦截点是 CSRF Origin。

## 修复

1. Django 在 DEBUG 模式下信任 `127.0.0.1` 和 `localhost` 的 Vite 开发端口 5173–5180，覆盖手动使用的 5176。生产模式不会自动信任这些 Origin，需用 `PROCESSPILOT_CSRF_TRUSTED_ORIGINS` 显式配置。
2. 保留原有 CSRF cookie/token 安全流程，没有放宽 view 权限。
3. 新增统一 `parseApiResponse()`：先读取 HTTP status、Content-Type 和文本，再决定是否解析 JSON。
4. CSV 上传改用同一解析器。HTML 403 现在显示 `HTTP 403：CSRF 校验失败...`，HTML 404 显示 `HTTP 404：API 不存在或 Vite 代理目标错误`，后端 JSON 错误同时保留 HTTP status 和原始 message。

## 修复后真实 HTTP 与浏览器验收

### A. “帮我找异常”

- `POST /api/agent/chat/live/` → 202 Accepted，`application/json`，返回 `skill_run_id`。
- `GET /api/agent/skill-runs/<id>/events/?after=<seq>` → 200 OK，`application/json`。
- 真实页面出现“实时执行” timeline，状态从“进行中”到“已完成”，无 403。

### B. `Steel_industry_data.csv`

- 浏览器 Request URL：`http://127.0.0.1:5176/api/pipeline/runs/`
- Method：POST multipart/form-data，携带 `X-CSRFToken`。
- Status：201 Created
- Response Content-Type：`application/json`
- Run：`20260912_201059_50db4811`
- 页面显示“已接收 Steel_industry_data.csv”及实时执行 timeline，无 JSON 语法错误。

### C. `xinan_completed_data.csv`

- 浏览器 Request URL：`http://127.0.0.1:5176/api/pipeline/runs/`
- Method：POST multipart/form-data，携带 `X-CSRFToken`。
- Status：201 Created
- Response Content-Type：`application/json`，Content-Length 179462
- Run：`20260912_201238_1ff5f256`
- 页面显示“已接收 xinan_completed_data.csv”及实时执行 timeline，无 JSON 语法错误。

### D. 不存在的 API

- 真实浏览器请求 `/api/definitely-missing/` 返回 404。
- 前端捕获为 `ApiError(status=404)`，显示 `HTTP 404：未知 API 表名`，不再抛出 `Unexpected token '<'`。

## 修改文件

- `heating_furnace_apc/settings.py`
- `.env.example`
- `frontend/src/api/client.js`
- `frontend/src/api/pipeline.js`
- `core/tests.py`
- `frontend/tests/api-client.test.js`
- `local_web_api_runtime_fix_report.md`

## 测试

- Django 完整回归：240 tests passed，1 skipped。
- 前端测试：20 passed。
- ESLint：通过。
- Vite production build：通过。
- 5176 真实 HTTP 请求、live polling 和两份 CSV 真实浏览器上传：通过。

### D. 不存在 API

真实浏览器调用 `/api/definitely-missing/` 返回 404，前端产生 `ApiError(status=404, message="HTTP 404：未知 API 表名")`，不再出现 `Unexpected token '<'`。HTML 404 分支也有独立自动测试。

## 修改文件

- `heating_furnace_apc/settings.py`
- `.env.example`
- `frontend/src/api/client.js`
- `frontend/src/api/pipeline.js`
- `core/tests.py`
- `frontend/tests/api-client.test.js`
- `local_web_api_runtime_fix_report.md`

本次未修改 Skill Resolution、Capability Resolver、Industrial Analysis、Scene Registry、字段统一、Segmentation、Optimization 或 Executor Runtime。
