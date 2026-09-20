# ProcessPilot A14

A14 用于工业时序数据的场景识别、字段与单位标准化、清洗、动态段筛选、系统辨识、离线预处理寻优，以及基于运行证据的问答、图文报告和数据导出。所有控制建议仅供离线评估，不向 PLC/DCS 下发指令。

## 功能与架构

- 数据资产：上传 CSV、检查字段与质量、复核映射、生成仿真数据、持久化资产及归档。
- 数值流程：时间对齐、缺失异常处理、SNR 估计、稳态/动态段筛选、时滞补偿、共线性处理、AR/ARX/FIRX 建模与诊断。具体模型及有效输入以运行证据为准。
- 离线寻优：冻结时间分区后选择候选，保留约束、失败和未改善原因；缺目标或质量不足不视为建模成功。
- Agent：理解任务、选择能力、编排执行、读取既有证据并解释结果；报告和导出请求可以复用现有任务，不必重新训练。
- 工程交付：运行追踪、CSV、含图 HTML、报告包和资产管理；缺失产物按实际状态显示。

Agent 的任务约束经校验后进入 Planner，MD Registry 从 `core/skills/**/SKILL.md` 加载能力、参数和依赖，Python Executor 调用 `integrations/` 中的实际算法。MCP 为动态筛选、解耦辨识、闭环寻优提供业务工具，以及状态、取消和产物摘要工具。知识检索辅助路由；模型回答不能替代算法证据、字段身份或安全门禁。

数据库保存任务、资产、知识和事件；运行目录保存输入副本、冻结分区、模型、指标与导出产物。只读解释与数值执行分别记录。场景统一定义在 `frontend/src/data/scenes.json`，点位字典 `integrations/standardization/knowledge/point_semantics.csv` 保留原公开论文来源；字段、单位、约束和算法 profile 在 `integrations/standardization/standards/scenarios/`。支持六个场景配置；三维模型目前仅覆盖高炉、脱丁烷塔、工业干燥器，其他场景会明确显示资源不可用。

## 目录

```text
core/                         API、服务、任务、迁移、MD Skill、正式测试
core/fixtures/regression/     正式测试所需的最小历史证据投影；不是本轮运行结果
frontend/                     Vue 前端、测试、场景配置与静态资源
heating_furnace_apc/           Django 配置与入口
integrations/                 标准化、清洗、辨识算法及功能资源
scripts/                      安装、开发启动、Python/MCP 启动器
examples/                     固定合成示例
acceptance/                   正式测试引用的路由评估工具
training/skill_router/         冻结路由模型的测试数据与质量门禁
datasets/                    数据来源元信息、合法获取/转换工具
tools/                       数据预检工具
deploy/                      反向代理配置
.github/workflows/            质量检查与既有标签发布工作流
```

项目总说明集中于本 README。Skill 的能力正文、引用、工作流以及第三方资源声明是功能或许可文件，需要随源码保留。

## 环境与安装

需要 Python 3.12+、Node.js 20.19+ 或 22.12+ 与 npm，首次安装需要网络。已在 macOS 26.0.1、Python 3.12.14、Node 24.18.0、npm 11.16.0、SQLite 的本机开发环境验证。Python 依赖使用 `requirements.txt` 中的版本范围；前端使用 `frontend/package-lock.json`，重新解析 Python 依赖可能获得不同版本。

在新 clone 的仓库根目录执行：

```sh
npm run setup
npm run dev
```

`setup` 会重建本目录 `.venv`、安装 Python 依赖、执行前端 `npm ci`、Django 检查、迁移和幂等知识初始化。不要在需要保留现有虚拟环境的目录直接重跑。找不到 Python 时，可通过 `PROCESSPILOT_BOOTSTRAP_PYTHON` 指定 Python 3.12+ 的可执行文件。

`dev` 统一启动 Django、后台 Worker、MCP Server 和 Vite，并执行迁移与知识初始化。默认入口：

- 驾驶舱：<http://127.0.0.1:5176/overview/>
- Agent：<http://127.0.0.1:5176/agent-review/>
- 数据资产：<http://127.0.0.1:5176/scenario-data/>
- 知识库：<http://127.0.0.1:5176/knowledge-base/>
- 后端健康检查：<http://127.0.0.1:8000/api/health/>
- MCP Streamable HTTP：`http://127.0.0.1:8010/mcp`

使用 Ctrl+C 停止开发启动器。仅初始化数据库时：

```sh
node scripts/python.mjs manage.py migrate --noinput
node scripts/python.mjs manage.py seed_knowledge_base
```

知识种子来自场景配置、Skill 契约和 `core/services/implementation_knowledge.py` 中的实现说明，不加载历史验收报告。仅 `approved` 知识参与检索；反馈不会自动改写生产规则。检索接口为 `GET /api/knowledge/search/?q=...`。

## 配置与 LLM

`.env.example` 仅含占位配置。在本地创建 `.env` 或通过环境注入真实值，不提交密钥、数据库或上传文件。例如：

```dotenv
APC_DB_ENGINE=sqlite
APC_SQLITE_NAME=apc_agent.db
PROCESSPILOT_RUNTIME_ROOT=runtime
DEEPSEEK_API_KEY=<your-own-key>
DEEPSEEK_MODEL=deepseek-flash
PROCESSPILOT_CSRF_TRUSTED_ORIGINS=http://127.0.0.1:5176,http://localhost:5176
```

在线模型可选择 DeepSeek；本地 OpenAI 兼容服务默认使用回环地址 `http://127.0.0.1:11434/v1`，模型名由实际服务决定。页面可测试配置；服务端已有密钥时页面无需再次填写。LLM 负责受约束任务理解、编排建议和基于证据的说明，数值结果由 Python 算法计算。在线失败或引用校验不通过时存在显式回退；Evidence 模式不调用在线模型，不能作为真实 LLM 验证。

端口必须通过终端环境传给 Node 启动器；仅写 `.env` 不保证改变 Node 端口。自定义前端端口时同时配置 CSRF Origin：

```sh
PROCESSPILOT_BACKEND_PORT=8050 \
PROCESSPILOT_MCP_PORT=8051 \
PROCESSPILOT_FRONTEND_PORT=5181 \
PROCESSPILOT_CSRF_TRUSTED_ORIGINS=http://127.0.0.1:5181,http://localhost:5181 \
npm run dev
```

独立启动命令有 `npm run backend`、`npm run worker`、`npm run dev:frontend`。MCP STDIO 使用 `npm run mcp`；HTTP 调试使用 `npm run mcp:http`。不要直接把开发服务或未经认证的 MCP 暴露到公网。

## 寻优终止状态与证据来源

搜索正常结束后，从成功完成有效评价的候选中按验证综合分选择最佳模型；覆盖率等质量约束单独显示，不阻止输出最佳模型、预测结果和报告。程序异常、输入条件不足、取消和超时分别显示。候选记录持续保存，刷新后可查看实际轮次与原因；历史缺失不补成零。

建模准备完成不代表模型已经拟合。参数越界、拟合失败或验证指标无效的候选不参与选优；没有可评价候选时仍明确终止，不制造模型。选择使用现有验证综合分（R²、误差与训练覆盖率），固定赢家后才评价测试集。未通过质量约束的最佳模型保留警告，不构成生产准入。旧的无赢家记录保持原样，重新运行会创建新任务。

聊天中的〔清洗记录〕、〔寻优记录〕等中文标签可以展开查看来源、阶段和事实。每条消息保留自己的任务与来源，切换任务、刷新或恢复历史不会改绑到最新任务。无法核验的来源明确降级；原始回答和后端引用校验保留。回答完成不代表数值流水线成功，读取停止原因不会自动重跑。

取消与超时在候选安全边界检查，不能强制中断正在执行的第三方数值库调用。显式重试创建新任务并关联源任务，保留既有证据。

## 使用流程与数据

1. 在数据资产页上传 CSV，或使用页面的仿真生成器。
2. 检查实际识别场景、字段单位与目标观测；需要人工复核时先处理缺口。
3. 运行清洗、筛选和建模，查看严格优质段、工程可用段、模型、验证/测试指标及失败原因。
4. 在 Agent 中绑定对应任务，查询结果，或明确请求离线寻优。
5. 请求“生成这次图文报告”“导出这次结果”，在交付页下载实际已生成的产物。

### 合成数据与演示模式

数据资产页提供“完整流程演示”“挑战测试”“自定义”。高炉候选预设为 `blast-furnace-demo-v3`（生成器 `causal-process-v3`），固定 seed `20260921`，1440 行、1 小时采样；4 个操纵量独立激励，低阶稳定动态过程，非零过程扰动与测量噪声、4 个局部输入尖峰，默认不注入目标尖峰。其他场景沿用明确标识的 `legacy_pressure_v1`，没有完整演示认证。

**当前认证状态：未通过。** 本版三份固定 seed 均跑通真实模型、寻优、预测、报告和导出，但 `20260921`、`20260922` 未全部达到预先声明的预测覆盖率／持续值基线要求，`20260923` 通过；因此不显示“已验证默认配置”，也不作为已验证推荐。完整流程预设仍可显式选择用于体验；修改参数自动转为自定义。验收目标见 `frontend/src/utils/demoAcceptance.json`，它是离线功能演示目标，不是工业标准。

操作：数据资产 → 选择模式 → 生成数据 → 开始完整分析 → 解耦辨识／闭环寻优 → 评审交付。生成只保存资产，不启动计算；可分别下载原始 CSV、生成清单和独立验收参考。资产、文件名、报告及导出保留 `SYNTHETIC` 合成标识。生成清单记录版本、显式 seed、参数、单位与 CSV SHA-256；参考文件单独存储、按资产权限下载，不进入选窗、模型特征、评分或 LLM 上下文。同一 CSV 下载再上传，仍走相同正式算法路径和质量门禁。

挑战模式保留高噪声、目标尖峰、过程冲击、稀疏目标、动态不足和旧版压力测试。允许保留带警告的最佳可评价模型，不能评价时明确终止；不保证自定义数据成功。当前仍按验证综合分选优，冻结赢家后评价测试集。通用修复只涉及候选边界投影／去重、自由仿真等待有效初始化历史及失败原因；没有调整场景约束、引入专用演示 Pipeline 或改变 best_available 排序。

`examples/synthetic_debutanizer.csv` 是稳定交付包中的固定合成示例，不代表真实装置验证。仿真生成实现位于 `frontend/src/utils/simulationCsv.js`；页面可生成高炉、脱丁烷塔和工业干燥器输入，也可在根目录执行：

```sh
node --input-type=module -e "import {writeFileSync} from 'node:fs'; import {buildDebutanizerSimulationCsv} from './frontend/src/utils/simulationCsv.js'; writeFileSync('synthetic.csv', buildDebutanizerSimulationCsv().csv);"
```

正式测试还保留既有合成干燥器夹具和归一化字段拒绝夹具；它们不是新工厂数据。`core/fixtures/regression/` 是既有记录中被断言使用的字段投影，保留来源关系、拒绝状态和哈希，不证明本次重新取得或运行了私有源文件。冻结路由模型的质量门禁也不代表生产准确率。

高炉示例 `frontend/public/datasets/blast_furnace_real_720h.csv` 来自 Vladimir Trofimov 的 [Mendeley 数据集](https://data.mendeley.com/datasets/6d7jbc7tb5/1)，DOI `10.17632/6d7jbc7tb5.1`，按 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 保留归属。它是 720 小时衍生切片：字段重命名，化验值仅向后对齐，容差 3 小时，保留缺目标行；原始工作簿未随本次发布。转换元信息及脚本位于 `datasets/real_candidates/blast_furnace_mendeley/`，需要重建时先从原来源取得对应工作簿，再运行转换脚本的 `--help` 查看参数。

Fortuna 脱丁烷塔公开镜像没有明确数据再分发许可，本仓库不发布该原始基准。来源为 [工业脱丁烷塔软测量镜像](https://github.com/Ujjwal-1267/industrial-debutanizer-soft-sensor)，参考 DOI `10.1016/j.conengprac.2004.04.013`。合法获取后可使用 `datasets/public/debutanizer/prepare_dataset.py`；派生时间轴只保存样本顺序，归一化数据缺少可信逆缩放元信息时不能当物理量输入，原说明中的 8 样本目标平移也必须保留。DAISY、LostRunes 等候选的字段/许可不足不会因测试夹具存在而变成完整数据验收；未随发布分发其私人原始文件。

## 测试与构建

```sh
npm test
```

根命令依次执行全部 `core` 后端测试、前端单元测试、lint 和构建；无需再把这些子步骤重复计作另一轮验证。单独调试可使用 `npm run test:backend`、`npm run test:frontend`、`npm --prefix frontend run lint`、`npm run build`。额外浏览器测试：

```sh
npm --prefix frontend exec playwright install chromium
npm --prefix frontend run test:e2e
```

数据库迁移一致性检查：`node scripts/python.mjs manage.py makemigrations --check --dry-run`。测试中因合法真实数据或可信物理元数据不足而跳过的项目，不算作通过。测试数据库与运行输出应使用独立路径，避免连接业务实例。

## 资产保留与部署边界

资产“删除”是归档：列表隐藏，按资产 ID 查询仍能看到 archived；既有任务引用的源副本保留，不等于物理抹除。运行数据清理默认只预览：

```sh
npm run runtime:prune -- --keep 100 --days 30
```

确认候选后才添加 `--apply`。先备份数据库及需要保留的运行产物，最新流水线结果按工具规则保留。

仓库保留 Docker、Nginx 和 CI 基线。生产部署需同源 HTTPS、独立认证与权限、持久数据库和运行目录、独立 Worker、备份和限流。相关环境变量包括 `PROCESSPILOT_DEBUG=0`、`PROCESSPILOT_REQUIRE_AUTH=1`、`PROCESSPILOT_SECRET_KEY=<random-secret>`、`PROCESSPILOT_ALLOWED_HOSTS`、`PROCESSPILOT_SECURE_SSL_REDIRECT=1`、`PROCESSPILOT_INLINE_WORKER=0`。MySQL 使用 `APC_DB_ENGINE=mysql` 及 `APC_DB_NAME/USER/PASSWORD/HOST/PORT`；Compose 还需 `APC_DB_ROOT_PASSWORD`。凭据由部署环境注入。可用 `manage.py check --deploy` 辅助检查，但它不构成生产准入。既有 `v*` 标签工作流会发布容器镜像；普通 main 推送只触发质量检查。

## 已知限制与许可

工程可安装、可交接不等于模型质量全面达标。筛选与寻优尚未证明存在普遍收益，真实工业场景验证范围有限，部分固定案例模型质量仍不足；在线 LLM 存在显式回退。当前没有现场控制投运或生产控制准入证明。Linux、Windows、容器部署和多租户环境不属于本机验证结论。

仓库未声明统一的项目开源许可证，本次发布不新增或改变授权。第三方数据、依赖和模型各自适用原许可。高炉数据归属与变更见上文；3D 资源归属、干燥器衍生模型许可及语义节点约束保留在 [3D 资源声明](frontend/public/models/README.md)。Draco 解码器的 [Apache-2.0 许可](frontend/public/draco/LICENSE) 随资源保留。项目自有冻结字段/路由模型仅用于辅助识别，不能替代测点物理身份校验。不得把公开可访问的工业数据自动视为可再分发数据。
