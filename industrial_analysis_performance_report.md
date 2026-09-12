# Industrial Analysis 性能优化报告

## 验收对象与结论

- 数据：`Steel_industry_data.csv`，35,040 行 × 11 列，15 分钟采样。
- 场景识别仍为 `steel_industry_energy`，显示名“钢铁工业能源监测”，必需字段覆盖率 100%。
- 受控基准从 165.3 s 降到 20.3 s，降幅 87.7%；原始真实页面基线约 195 s。
- 真实浏览器上传后 5.0 s 产生首个可用回答，12 s 完成全部深度流水线。页面不再等待全流水线才显示结果。

## 真实 timing trace

最终浏览器运行 `20260912_210907_d87c6697`：

主流水线的 `start_time/end_time/elapsed_ms` 保存在 snapshot `stages[]`；CSV 上传、parse、场景识别和字段标准化的同样三项时间保存在 `performance_spans`。Skill 规划、capability 和回答阶段分别保存在 Skill Plan `timing_trace`、Industrial Analysis `timing_trace` 和 Runtime Events，表中是这些原始 span 的耗时汇总。

| 阶段 | 耗时 |
|---|---:|
| CSV 上传持久化 | 6.528 ms |
| CSV parse | 25.486 ms |
| scene recognition | 389.911 ms |
| field standardization | 1,347.068 ms |
| standardization 整体 | 2,109 ms |
| data quality / cleaning | 1,832 ms |
| selection | 17 ms |
| modeling plan/frozen split | 13 ms |
| validated modeling + optimization | 8,222 ms |
| review | 12 ms |
| report generation | 13 ms |
| Task Understanding | 4.966 ms |
| Candidate Recall | 105.055 ms |
| DataContext | 4.263 ms |
| Skill Discovery | 40.566 ms |
| Capability Resolution | 0.120 ms |
| Skill loading | 21.634 ms |
| Workflow Planning | 0.010 ms |
| Execution Plan | 0.005 ms |
| DATA_PROFILING | 5.398 ms |
| DATA_QUALITY_ANALYSIS | 15.234 ms |
| ENERGY_ANALYSIS | 7.638 ms |
| TREND_ANALYSIS | 49.616 ms |
| 共享数值特征准备 | 9.458 ms |
| Skill CSV load | 39.372 ms |
| answer generation | 1 ms |

`TIME_SERIES_ANALYSIS`、`ANOMALY_DETECTION`、`CORRELATION_ANALYSIS`、`PROCESS_STABILITY` 未被该开放式快速请求选中，因此耗时为“未执行”，而不是 0 ms。大型 visualization 也未进入本轮后端 capability 计划；前端结果卡和 timeline 随轮询同步更新。

## 最耗时 Top 5

| 排名 | 阶段 | 优化后 |
|---:|---|---:|
| 1 | validated modeling + optimization | 8,222 ms |
| 2 | standardization 整体 | 2,109 ms |
| 3 | data quality / cleaning | 1,832 ms |
| 4 | field standardization 子阶段 | 1,347 ms |
| 5 | scene recognition | 390 ms |

优化前的决定性瓶颈是 validated modeling：13 个模型候选每次在 rolling 10-step 验证中，对每个评估终点复制完整 `y` 历史，并通过约 99.5 万次 Pandas `iloc` 递推。单个 profiling 运行为 1.09 亿次函数调用 / 34.36 s，导致 optimization 阶段基线约 156.6–186 s。

## 重复计算与复用

- rolling multi-step 预测改为按所有评估终点的 NumPy 矩阵批处理，只保留固定 10 步递推，不改变测量输出反馈边界。
- free simulation 仍保留必需的时序递归，但移除逐行 Pandas `iloc`、Series 取值和重复拷贝。
- 时滞估计对分段 ID、输入和输出数组预计算，避免每个 lag 重复 `concat/groupby`。
- Industrial Analysis Executor 在同一请求中共享 numeric matrix、missing rates 和 correlation matrix；相关性只处理数值且非常量字段。
- `run_id` 直接复用 pipeline snapshot/artifact 构建 DataContext；Skill Runtime 不再重跑场景识别和字段统一。
- snapshot 改为唯一临时文件原子替换，避免后台写入时前端读到半截 JSON。

## Capability 成本和规划预算

- LOW：`DATA_PROFILING`、`DATA_QUALITY_ANALYSIS`、`MISSING_DATA_ANALYSIS`。
- MEDIUM：`TREND_ANALYSIS`、`ENERGY_ANALYSIS`、`CORRELATION_ANALYSIS`、`TIME_SERIES_ANALYSIS`、quick `ANOMALY_DETECTION`。
- HIGH：`PROCESS_STABILITY`、`ROOT_CAUSE_CANDIDATES`、`SEGMENTATION`、`MODELING`、`OPTIMIZATION`。

每个候选新增 `estimated_cost`、`expected_value` 和 `planning_value`；关键词仍只是低权重召回信号。默认 `analysis_budget` 为：

```json
{
  "mode": "fast",
  "max_capabilities": 6,
  "max_runtime_seconds": 15,
  "max_high_cost_capabilities": 1
}
```

用户明确要求“完整深度分析”时切换为 `extended`：上限 10 项 capability、4 项 HIGH、60 s Runtime 预算。

开放式上传的 Fast Path 选择两个 LOW 和最多两个场景相关 MEDIUM capability。当前 Steel 实测为 `DATA_PROFILING + DATA_QUALITY_ANALYSIS + ENERGY_ANALYSIS + TREND_ANALYSIS`。复杂异常、深度时序、稳定性和根因候选只在语义明确且前置条件满足时进入 extended analysis。

## Fast Path 和 UI

`POST /api/pipeline/runs/` 在 `async_analysis=true` 时于创建 run snapshot 后返回 HTTP 202。前端轮询该 run，标准化和清洗证据可用后立即启动基础 Industrial Analysis，然后清除整页 loading。深度辨识、寻优、评审和报告继续后台运行，页面显示“基础结果可用 · 深度分析进行中”，最终追加深度分析完成消息。

异步上传是 Web 的显式选项；原有同步 API 调用保持兼容。后台任务完成或失败都会停止轮询并产生明确状态，不再留下永久 spinner。

## Before / After

| 指标 | Before | After |
|---|---:|---:|
| 首个页面可用结果 | 约 195 s（等全流水线） | 5.0 s |
| 受控全流水线 | 165.3 s | 20.3 s |
| 真实浏览器全流水线 | 约 195 s | 12 s |
| 进程 maximum RSS | 178.5 MiB | 204.2 MiB |
| 进程 peak memory footprint | 178.4 MiB | 179.5 MiB |
| 快速 capability | 等待流水线后统一返回 | 4 项，共 77.9 ms |
| 共享 cache | 无 | numeric/missing/correlation |

RSS 峰值在两次独立进程测量中有波动，本次性能收益来自计算复杂度下降，没有用采样或缩减验证集换取速度。同版本优化前/后测试集指标完全一致：`R²=0.8788936857361089`、`RMSE=11.838048405767262`、`MAE=5.348147962147686`，最优轮次均为 13，得分均为 63.411。

## 修改文件

- `core/services/pipeline.py`
- `core/pipeline_api.py`
- `core/skills/context.py`
- `core/skills/capability_resolver.py`
- `core/skills/runtime.py`
- `core/skills/industrial-analysis/executor.py`
- `core/skills/industrial-analysis/scripts/build_analysis_plan.py`
- `integrations/identification/validated_modeling.py`
- `integrations/standardization/standard_agent/engine.py`
- `frontend/src/api/pipeline.js`
- `frontend/src/views/AgentWorkflowView.vue`
- `core/test_skill_routing.py`
- `core/tests.py`

## 验证

- Django：244 tests passed，1 skipped。
- Frontend：22 tests passed。
- ESLint：38 JavaScript/Vue files passed。
- Vite production build：passed。
- 真实 Playwright 浏览器：上传 35,040 × 11 Steel CSV，基础回答在 5.0 s 可见；后台完成后出现“深度分析已在后台完成”；任务状态为 completed，无持续 spinner。

## 剩余瓶颈和限制

- 全流水线最大剩余成本仍是多候选 validated modeling + optimization，当前约 8–12 s。
- 本地异步执行使用 Django 进程内后台线程；开发服务热重载或进程重启会中断正在执行的深度任务。部署环境应改用持久任务队列。
- `max_runtime_seconds` 已在 capability 边界检查并记录 `timeout_reason`；当前不会强制中断正在 NumPy/Pandas 内核中执行的单项计算。
