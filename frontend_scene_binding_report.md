# Frontend Scene Binding Report

## 结论

问题来自前端将项目预设场景用于最近运行筛选、说明卡和部分回退数据。上传数据虽已由后端识别为另一场景，页面仍可能继续展示项目场景内容。修复只调整前端状态与展示绑定，没有改动场景识别算法或 `industrial-analysis` Skill。

## 统一状态

前端现通过 `useSceneBinding.js` 生成：

```json
{
  "project_scene": { "id": "", "display_name": "" },
  "data_scene": { "id": "", "display_name": "", "status": "", "confidence": 0, "source": "" },
  "is_mismatch": false
}
```

数据场景取值顺序为 `final_scene → selected_scene → agent_scene → detected_scene → scene_id → standardization.scenario`。名称优先读取 API 返回的 `scenario_name/name/display_name`。

## 绑定规则

- 顶部项目选择器继续使用 `project.scenarioId`，上传不会修改项目配置。
- 数据资产、概览场景说明、工业孪生、Agent 轨迹回退和标准化证据卡使用最近运行的 `data_scene`。
- 所有数据页读取未按项目场景过滤的最近运行，页面刷新先恢复本地最近快照，再以 `/api/pipeline/runs/latest/` 更新。
- 项目场景与数据场景不同会显示非阻塞提示；本次数据处理仍使用自动识别场景。

## 验证

场景状态测试覆盖：锅炉数据与脱丁烷塔项目不一致、蒸气压力候选场景、真实脱丁烷塔数据一致、最终场景优先级。前端生产构建用于检查全部组件编译与依赖。

浏览器三组上传的预期绑定分别为：

1. `xinan_completed_data.csv`：项目场景保持 `debutanizer_column`，数据场景显示 `thermal_power_boiler_long_tail`，显示 mismatch，说明卡跟随锅炉场景。
2. `vapor-pressure.csv`：数据场景切换为 `vapor_pressure_soft_sensor`，说明卡同步切换。
3. debutanizer 数据：项目场景与数据场景均为 `debutanizer_column`，显示场景一致。

本报告只确认前端对后端快照的绑定行为；数据识别正确性由既有后端真实运行结果负责。

## 修改文件

核心修改位于 `frontend/src/composables/useSceneBinding.js`、`useLatestPipelineRun.js`、`App.vue`、数据与工作流页面、场景说明/孪生/证据/轨迹组件以及 `frontend/src/styles/base.css`。测试位于 `frontend/tests/sceneBinding.test.mjs`。
