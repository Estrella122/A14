# Core Skill Runtime 最终收口验收

## 端到端 DAG

| 案例 | ExecutionPlan | 结果 |
|---|---|---|
| 找出这批数据里最适合建模的动态工况段 | standardization → cleaning → segmentation | 不执行 modeling |
| 用已有模型和这批数据优化运行参数 | optimization | 只在 Runtime State 有完整 optimization contract 时执行 |
| 帮我优化运行参数 | optimization | 缺 objective/model/bounds/constraints 等则 blocked |
| 重新找最优动态段并重新建模，再优化 | standardization → cleaning → segmentation → modeling → optimization → review | 全部由核心 Executor 执行；优化策略合同必须由 snapshot/planner 显式提供 |

分析类 anomaly 请求不会因 capability 文档依赖生成核心数据变更 DAG，仍由 industrial-analysis Executor 处理。

## 失败传播

Executor DAG 顺序执行。某节点为 failed、blocked 或 unavailable 时，依赖它的后续节点返回 blocked，并记录 `前置 Executor 未成功`；不会从旧 snapshot 或 Pipeline bundle 隐式补齐。

## Artifact resolution

新增 `RuntimeArtifactRef` 与 `RuntimeArtifactResolver`，统一保存 run_id、skill_id、artifact type、path/ref、version、created_at 和 source execution id。Executor 优先消费本轮 state 中注册的 artifact，再读取 snapshot 声明的 artifact。

## 模式验收

- hybrid：八个核心 Skill 使用 Executor，核心路径 `fallback_used=false`。
- skill_runtime：缺前置合同返回 blocked，缺 Executor 返回 unavailable；不调用 `rerun_pipeline()`。
- legacy：旧完整 Pipeline 保留。
- Report/Review 继续只消费既有结果。

## Pipeline 回归

使用真实 `xinan_completed_data.csv` 在临时运行目录完成全流程：standardization、cleaning、selection、modeling、optimization、review、report 全部 completed；生成 segmentation 五类 artifact；optimization 记录 `test_evaluations=1`。

## 真实 Skill Runtime 组合链

使用真实 xinan 数据和显式 optimization contract 执行案例 D，运行 `skillrun_7bbfef24d227`：

- DAG：standardization → cleaning → segmentation → modeling → optimization → review。
- 六个核心 Executor 全部 success，`fallback_used=false`。
- optimization evidence：`test_used_for_search=false`、`test_evaluation_count=1`、`synthetic_fallback=false`。
- 顶层运行状态为 partial，唯一原因是该请求没有显式选中非核心治理能力 `execution_supervisor_replanner`，其在当次运行计数中为 unavailable；核心执行链无 blocked/failed。最新远程基线已为该能力注册独立 Executor，显式重规划请求可执行。

## 自动化测试

- 全量 Django：220 tests，全部通过，1 skipped。
- 新增 segmentation/optimization/runtime 专项测试 36 个，全部通过，覆盖独立执行、前置条件、泄漏保护、产物、统一结果合同、synthetic 禁止、四条验收 DAG、失败传播与 artifact provenance。
- 真实 segmentation service 与真实 optimization Executor 另行完成数据验收。

## 剩余限制

- 当前 Optimization Skill 对应 Catalog 的“闭环预处理寻优”，输出是离线候选策略，不是生产闭环控制指令。
- 多输出模型在 legacy Pipeline 中按每个输出各测试一次；独立 Optimization Executor 本轮只处理主输出，从而保证其合同中的 test count 为 1。
- RuntimeArtifactRef 当前是进程内结构与 snapshot adapter，尚未迁移为数据库实体。
