# 生产化补强验收记录

## 已完成范围

1. 闭环候选增加安全评估、人工审批记录和强制 `actuation_allowed=false`；审批只授权影子试运行。
2. 流水线、Agent 任务、流水线快照和 Skill 事件改为数据库持久化；独立 Worker 支持失联任务重排与有界重试。
3. `ENERGY_ANALYSIS`、`EQUIPMENT_HEALTH`、`QUALITY_ANALYSIS`、`OPERATING_STATE`、`BOTTLENECK_ANALYSIS`、`ROOT_CAUSE_CANDIDATES` 补齐专用统计执行逻辑，不再伪装成通用上下文成功。
4. 30 个业务 Skill 均保留机器可读输入、输出、执行方式和质量闸门契约。
5. 增加 GitHub Actions、MySQL/API/Worker/Nginx Compose 基线、健康检查和生产部署说明。
6. 增加 Playwright 桌面与移动浏览器测试；修复移动导航造成的页面横向漂移和搜索按钮挤压。
7. 三维模块改为按需加载，Agent 与流水线轮询使用自适应退避。
8. 前后端共用 `frontend/src/data/scenes.json` 场景清单；新增场景无需修改场景识别或 3D 注册代码。

## 自动验收结果

- Django：265 项通过，1 项跳过。
- 前端单元测试：28 项通过。
- ESLint：通过。
- Vite 生产构建：通过。
- Playwright 桌面 Chromium：3 项通过。
- Playwright 移动 Chromium：3 项通过。
- Django `check --deploy`：无问题。
- 迁移一致性：无未生成迁移。
- 数据库队列实测：流水线任务一次领取并完成；Agent 任务一次领取，9 条事件持久化并完成。

## 明确边界

本次完成的是生产化软件基线，不包含真实 DCS/PLC/OPC UA 下发适配器。现场闭环必须另行取得协议、点表、安全联锁和投运授权，并完成 SIL/HIL、影子运行、双人复核和故障回退验收。在这些条件满足前，系统始终只输出离线候选策略。
