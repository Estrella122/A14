# 七项工程要求整改与验收记录

验收日期：2026-09-12

本记录以《要求.rtf》的七项审查结论为验收基线。结论严格区分“功能已实现”“已有自动化证据”和“仍需外部数据才能通过”，不把合成数据或离线结果表述为生产验收。

## 1. Skill 执行能力

状态：工程整改完成。

- `engineering_visualization_builder`、`industrial_simulation_generator`、`experiment_tracker_comparator`、`execution_supervisor_replanner` 均已注册独立 Executor。
- 可视化只消费真实流水线预测序列；缺少证据时阻断，不生成占位图。
- 仿真生成器输出确定性 CSV，并在结果中写入 `synthetic: true`、随机种子和告警。
- 实验比较从真实流水线运行注册表读取独立测试指标。
- 执行监督可检查失败节点与流水线失败阶段，并落盘重规划动作。
- `summary.executed` 根据实际 Executor 调用计算，不再固定为 0。

自动化证据：`core.test_core_skill_executors`。

## 2. Agent 真实用户准确率

状态：验收机制完成，生产准确率仍待外部验收集。

- `acceptance/evaluate_real_routing.py` 支持按会话分组、防数据泄漏、未知意图拒绝率及关键误执行统计。
- `acceptance/reports/real_routing_acceptance.json` 明确设置 `production_accuracy_claim: false`；在真实人工批准样本不足时返回 `insufficient_evidence`。
- 不用人工编写的合成问题冒充真实用户验证。达到生产声明仍需采集并独立标注 300～500 条真实请求。

## 3. Web 真实执行与数据来源

状态：工程整改完成。

- 可视化流水线通过 `/api/pipeline/workflow/execute` 执行后端规范 DAG。
- 实验追踪无后端记录或请求失败时显示空态/错误，不回退 mock 记录。
- 数据优选、系统辨识页面已移除预置片段、相关矩阵和时滞结果；缺少真实任务时显示空态。
- 仿真入口保留，但文案与结果显式标记为仿真数据。

## 4. 生产安全

状态：代码基线完成；部署仍必须按环境配置执行。

- 生产模式默认要求 Django 登录会话，写请求保留 CSRF 校验。
- 已移除业务接口的 `Access-Control-Allow-Origin: *`。
- 上传限制包含文件大小、最大行数与最大列数。
- 生产配置支持 HTTPS 重定向、安全 Cookie、HSTS、独立密钥与主机白名单。
- 发布前必须按 `docs/production_deployment.md` 配置反向代理、身份、密钥与持久卷。

## 5. 测试隔离

状态：工程整改完成。

- 流水线与 Skill 产物统一受 `PROCESSPILOT_RUNTIME_ROOT` 控制，CI 可指向临时目录。
- 后端测试通过临时目录 patch 隔离运行产物。
- 前端提供单元测试、源码/SFC lint 和生产构建检查。

## 6. 建模工程投运标准

状态：质量门禁完成，当前模型仍不允许宣称投运就绪。

- 当前模型证据报告的测试 R² 为 0.7879，相对持续值基线 RMSE 改善 21.32%。
- 但当前最佳模型为 AR，未拟合外部输入，因此 `model_evidence_acceptance.json` 仍以 `blocked` 结论阻止软测量或闭环 APC 投运声明。
- 后续只有在新增真实工况数据、外部输入贡献验证、受控验证与联锁评审全部通过后，才能改变此结论。

## 7. 其他工程问题

状态：工程整改完成。

- 优化 API 支持通过 `dataset_mode=uploaded_csv` 与 `pipeline_run_id` 登记真实 CSV 流水线寻优结果。
- Vue 页面按路由懒加载，ECharts 运行时拆分为独立缓存块。
- `manage.py prune_runtime` 支持按数量/天数 dry-run 与确认后清理，并始终保护最新流水线运行。
- 项目已纳入 Git 版本管理；本次变更通过提交与远端分支保留审计记录。

## 自动化验收命令

```bash
npm test
PROCESSPILOT_DEBUG=0 \
PROCESSPILOT_REQUIRE_AUTH=1 \
PROCESSPILOT_SECRET_KEY='<至少 50 位随机密钥>' \
PROCESSPILOT_ALLOWED_HOSTS='processpilot.example.com' \
.venv/bin/python manage.py check --deploy
```
