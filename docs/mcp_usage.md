# ProcessPilot MCP 使用说明

## 1. 初始化

```bash
cd "/path/to/A14-production-hardening"
npm run setup
```

`setup` 会安装官方 Python MCP SDK、执行数据库迁移并初始化经过审核的知识库。

初始化完成后，推荐使用统一开发启动命令：

```bash
npm run dev
```

该命令会检查并启动 Django API、Runtime Worker、MCP Server 和 Web 前端。浏览器仍通过 Django API 工作；只有三个工业计算模块由 Django Agent 通过 MCP 调用。

默认端口为前端 `5176`、Django `8000`、MCP `8010`。若本机端口冲突，可只为本次启动覆盖端口：

```bash
PROCESSPILOT_FRONTEND_PORT=15176 \
PROCESSPILOT_BACKEND_PORT=18000 \
PROCESSPILOT_MCP_PORT=18010 \
npm run dev
```

启动器会同步调整 Vite 代理与 Django 使用的 MCP 地址，不需要再手改配置文件。

## 2. 本地 STDIO

直接启动：

```bash
npm run mcp
```

接入支持 MCP 的桌面客户端时，使用项目虚拟环境中的 Python 和绝对脚本路径：

```json
{
  "mcpServers": {
    "processpilot-modeling": {
      "command": "/absolute/path/to/A14-production-hardening/.venv/bin/python",
      "args": [
        "/absolute/path/to/A14-production-hardening/scripts/mcp_server.py"
      ],
      "env": {
        "PROCESSPILOT_MCP_TRANSPORT": "stdio",
        "PROCESSPILOT_INLINE_WORKER": "true"
      }
    }
  }
}
```

不同客户端的配置文件位置不同，但 `command`、`args` 与 `env` 的含义相同。不要使用系统 Python，以免缺少项目依赖。

## 3. 本机 HTTP 调试

```bash
npm run mcp:http
```

默认端点：`http://127.0.0.1:8010/mcp`。

该入口默认只绑定本机。项目尚未为 MCP 远程入口实现用户认证，不要直接暴露到公网。生产部署需增加 OAuth/反向代理鉴权、权限、限流和 TLS。

## 4. 标准调用流程

1. 使用 `list_registered_runs` 找到包含 `SOURCE_DATA` 的真实运行。
2. 调用 `run_dynamic_selection(source_run_id=...)`。
3. 保存返回的 `job_id`，使用 `get_job_status` 查询完成状态。
4. 对需要时滞、共线性和 AR/ARX 建模的任务调用 `run_decoupling_identification`。
5. 对需要预处理反馈搜索的任务调用 `run_closed_loop_optimization`。
6. 使用 `list_run_artifacts` 和 `get_artifact_summary` 检查证据，不要要求模型读取完整工业 CSV。

三个计算工具都会基于源运行创建新的不可覆盖运行，不修改历史证据。建议每次提交提供调用方唯一的 `idempotency_key`，防止 Agent 重试时重复计算。

## 5. 工具与资源

计算工具：

- `run_dynamic_selection`
- `run_decoupling_identification`
- `run_closed_loop_optimization`

只读或任务工具：

- `get_job_status`
- `cancel_job`
- `list_registered_runs`
- `list_run_artifacts`
- `get_artifact_summary`
- `search_knowledge`

Resources：

```text
processpilot://server/capabilities
processpilot://skills/catalog
processpilot://skills/{skill_id}/contract
processpilot://scenes/{scene_id}/contract
processpilot://runs/{run_id}/manifest
processpilot://runs/{run_id}/evidence
```

## 6. 状态语义

- `queued`：已持久化，等待 Worker。
- `running`：正在计算。
- `completed`：计算完成，不等于可生产投运。
- `partial`：有可用结果，但存在明确限制。
- `blocked`：质量门禁或前置条件不足；这是安全阻断，不是服务器故障。
- `failed`：算法或基础设施执行失败。
- `cancelled`：任务已取消。

所有结果固定包含：

```json
{
  "control_mode": "advisory_only",
  "actuation_allowed": false
}
```

MCP 不提供 PLC/DCS 写入工具。闭环寻优仅表示离线预处理—建模—验证反馈搜索。

## 7. Agent 可视化契约

MCP 本身不渲染界面。计算工具与 `get_job_status` 固定返回
`processpilot-mcp-observability-v1` 可观测契约，供 Agent 页面直接展示真实执行时间线：

```json
{
  "observability_schema_version": "processpilot-mcp-observability-v1",
  "job_id": "job_xxx",
  "tool_name": "run_dynamic_selection",
  "status": "running",
  "current_stage": {
    "key": "selection",
    "label": "动态检测、SNR 估算与数据段评分",
    "status": "running",
    "message": "正在冻结优质动态数据段"
  },
  "progress": {"completed": 2, "total": 3, "percent": 66.7},
  "execution_timeline": [
    {
      "sequence": 1,
      "stage": "standardization",
      "label": "数据与字段校验",
      "status": "completed",
      "message": "字段标准化完成",
      "started_at": "...",
      "finished_at": "...",
      "elapsed_ms": 120
    }
  ]
}
```

Agent 调用端只在任务状态、阶段或百分比发生变化时发布事件，避免轮询造成重复记录。
用户界面可以展示工具名、任务编号、当前阶段、进度、质量门禁和产物数量；不得展示或伪造
Agent 的私有推理过程。
