# 生产部署基线

本项目的生产入口应由同一个 HTTPS 域名反向代理：静态前端由 Web 服务器提供，`/api/` 与 `/admin/` 转发给 Django。不要把 Django 开发服务器或 Vite 开发服务器暴露到生产网络。

## 必需环境变量

```bash
PROCESSPILOT_DEBUG=0
PROCESSPILOT_SECRET_KEY=<至少 50 位的随机密钥>
PROCESSPILOT_ALLOWED_HOSTS=processpilot.example.com
PROCESSPILOT_REQUIRE_AUTH=1
PROCESSPILOT_SECURE_SSL_REDIRECT=1
PROCESSPILOT_HSTS_SECONDS=31536000
PROCESSPILOT_SIMPLEUI=0
PROCESSPILOT_RUNTIME_ROOT=/var/lib/processpilot/runtime
PROCESSPILOT_MAX_CSV_ROWS=1000000
PROCESSPILOT_MAX_CSV_COLUMNS=500
PROCESSPILOT_INLINE_WORKER=0
PROCESSPILOT_JOB_STALE_SECONDS=900
```

数据库凭据应由部署平台注入，不要写进 `.env` 或版本库。需要 MySQL 时设置 `APC_DB_ENGINE=mysql` 以及 `APC_DB_NAME`、`APC_DB_USER`、`APC_DB_PASSWORD`、`APC_DB_HOST`、`APC_DB_PORT`。

## 可恢复后台任务

流水线与 Agent 实时任务先写入 `runtime_jobs`，生产环境必须单独启动 Worker：

```bash
python manage.py run_runtime_worker
```

Worker 异常退出后，超过 `PROCESSPILOT_JOB_STALE_SECONDS` 的运行中任务会重新入队；流水线快照和 Skill 事件同时写入数据库，本地 JSON/JSONL 只作为可移植产物副本。`GET /api/health/` 用于就绪检查，`GET /api/runtime/jobs/<job_id>/` 用于任务诊断。

## 闭环安全边界

寻优结果始终标记为 `offline_candidate_only` 且 `actuation_allowed=false`。真实上传数据且全部硬约束通过后，只能申请“影子试运行”审批；即使审批通过，也不会产生 DCS/PLC 指令。接入现场控制必须在独立项目中完成联锁、权限、双人复核、SIL/HIL 和回退验收，不能通过修改前端状态绕过。

## 容器启动

仓库提供 API、数据库 Worker、MySQL 和 Nginx 前端的 Compose 基线。启动前必须从密钥系统注入 `PROCESSPILOT_SECRET_KEY`、`APC_DB_PASSWORD` 与 `APC_DB_ROOT_PASSWORD`，然后执行 `docker compose up --build`。数据库和运行产物使用独立持久卷。

## 发布检查

```bash
PROCESSPILOT_DEBUG=0 \
PROCESSPILOT_REQUIRE_AUTH=1 \
PROCESSPILOT_SECRET_KEY='<production-secret>' \
PROCESSPILOT_ALLOWED_HOSTS='processpilot.example.com' \
.venv/bin/python manage.py check --deploy

npm run test
npm run build
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
```

首次部署使用 `manage.py createsuperuser` 创建独立管理员。用户先在 `/admin/login/` 建立会话，再访问业务页面；所有 `/api/` 接口在生产模式下要求有效会话，写操作同时校验 CSRF Token。不要共享管理员账号。

推送 `v*` 版本标签后，发布工作流会先重复执行后端、前端、lint 和构建验收，再把 API 与 Web 镜像发布到 GitHub Container Registry。部署环境应按变更审批流程显式拉取该版本，不能自动覆盖正在运行的现场实例。

## 反向代理要求

- 仅开放 HTTPS，并把 `X-Forwarded-Proto: https` 传给 Django。
- 前端、`/api/` 和 `/admin/` 保持同源，避免扩大 CORS 与 Cookie 范围。
- 限制请求体大小；Django 默认将内存请求限制为 5 MiB，可用 `PROCESSPILOT_UPLOAD_MEMORY_BYTES` 调整。
- 对登录接口设置速率限制，并在代理或身份系统中记录审计日志。
- 运行目录和数据库应放在持久卷中，并纳入备份；不要备份前端构建缓存。

## 运行数据保留

清理命令默认只输出候选清单，不删除文件：

```bash
npm run runtime:prune -- --keep 100 --days 30
```

人工确认后才添加 `--apply`。命令只会处理项目定义的运行产物目录，并始终保留最新一次流水线结果。
