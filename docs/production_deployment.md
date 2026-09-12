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
```

数据库凭据应由部署平台注入，不要写进 `.env` 或版本库。需要 MySQL 时设置 `APC_DB_ENGINE=mysql` 以及 `APC_DB_NAME`、`APC_DB_USER`、`APC_DB_PASSWORD`、`APC_DB_HOST`、`APC_DB_PORT`。

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
