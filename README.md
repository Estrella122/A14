# ProcessPilot A14

面向工业时序数据的场景识别、字段与单位标准化、因果清洗、动态段筛选、AR/ARX 系统辨识、离线寻优和工程评审系统。

当前正式保留三套比赛场景：钢铁高炉铁水质量预测、炼油脱丁烷精馏塔和工业干燥器。高炉场景提供带 CC BY 4.0 来源说明的 Mendeley 真实过程数据演示切片，并对非等间隔铁水化验采用只向后匹配的因果对齐；脱丁烷塔保留30–75分钟测量滞后和物理量字段规则；工业干燥器支持10秒采样、3输入3输出及共享输入的多输出ARX模型组。离线指标通过不代表已经具备生产投运条件。

## 环境

- Python 3.12+
- Node.js 20.19+ 或 22.12+

## 安装与运行

```bash
npm run setup
npm run dev
```

`npm run setup` 会在下载后的本地工程中创建 `.venv`、安装 Python 和前端依赖，执行数据库迁移并幂等初始化知识库。浏览器入口为：

- Agent 中枢：<http://127.0.0.1:5176/agent-review/>
- 项目驾驶舱：<http://127.0.0.1:5176/overview/>
- 工业知识库：<http://127.0.0.1:5176/knowledge-base/>
- 后端 API：<http://127.0.0.1:8000/api/>

## Agent 大模型

复制 `.env.example` 为 `.env` 后，可在服务端配置 DeepSeek；真实密钥不得提交：

```bash
DEEPSEEK_API_KEY=your-server-side-key
DEEPSEEK_MODEL=deepseek-flash
```

Agent 中枢允许用户选择 Evidence Agent、DeepSeek 或本地 OpenAI 兼容模型。本地模式默认连接 `http://127.0.0.1:11434/v1`，可在页面中修改模型名与回环地址，适用于 Ollama、LM Studio 等服务。浏览器不会读取或保存服务端密钥。运行时先完成场景识别、Capability/Skill 解析和 Executor 执行，再把有限的结构化证据交给模型生成回答；界面展示的是可审计判断摘要，不是模型隐藏思维链。

上传数据成功且无需人工映射复核时，前端会按后端识别出的 `scenario_id` 切换项目上下文并打开对应三维场景。后续仓库组织者提供完整算法时，应继续通过现有 Skill catalog、Executor 和 artifact registry 注册；未安装模块保持 `waiting`/`unavailable`，不得用模拟结果冒充执行成功。

## 验证

```bash
npm run test:backend
npm run test:frontend
npm run build
npm --prefix frontend run test:e2e
```

运行产物清理默认只预览；确认清单后再执行：

```bash
npm run runtime:prune -- --keep 100 --days 30
npm run runtime:prune -- --keep 100 --days 30 --apply
```

高炉演示可直接上传 `frontend/public/datasets/blast_furnace_real_720h.csv`；工业干燥器可上传 `演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv`。后者是合成验收数据，不代表真实工厂数据。

脱丁烷塔数据的上游公开副本没有明确再分发许可证，因此仓库仅保留适配代码和来源说明，不重新发布数据文件。取得合法数据副本后，按 `datasets/public/debutanizer/README.md` 操作。

更完整的说明见 [使用说明.md](使用说明.md)，知识库设计见 [docs/knowledge_base.md](docs/knowledge_base.md)，上线评审要求见 [docs/deployment_acceptance.md](docs/deployment_acceptance.md)，生产安全配置见 [docs/production_deployment.md](docs/production_deployment.md)。

场景清单统一维护在 `frontend/src/data/scenes.json`；新增场景先登记 ID、别名和三维资产状态，再添加标准化模板。生产后台任务使用数据库队列，开发模式会自动唤醒内置 Worker，生产模式应运行独立的 `npm run worker`。

## 文档导航

数据需求、当前验收与架构说明统一见[项目文档入口](docs/README.md)。
