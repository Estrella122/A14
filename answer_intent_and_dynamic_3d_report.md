# Answer Intent 与动态 3D 改造报告

## 改造结果

本次将“分析什么”与“怎样回答”分离，并将数字孪生页的模型选择从项目预设场景切换为真实数据场景。Capability Resolver、Artifact Resolver、Executor Runtime、分段/优化核心算法、Field Registry 和 Scene Recognition 未修改。

## Answer Intent

TaskSpec 新增 `answer_intent`，包含 `kind`、`confidence`、`signals` 和 `source`。支持 `VALUE_QUERY`、`METHOD_QUERY`、`FORMULA_QUERY`、`EVIDENCE_QUERY`、`INTERPRETATION_QUERY`、`COMPARISON_QUERY`、`CAUSE_QUERY`、`RECOMMENDATION_QUERY`。

回答形式不参与 Capability 最终选择，因此不会为了回答“怎么算”而重新执行 Pipeline。SNR 回答会读取当前 run 的 `snr_estimates.csv` 和 cleaning snapshot 的 method、threshold、calibrated、assumptions，再按 Answer Intent 组织。

实际 `snr_details()` 方法：

- 二阶差分 `Δ²x`
- `σ̂ = MAD(Δ²x) / (0.67448975 × √6)`
- `noise_power = σ̂²`
- `signal_power = max(Var(x) - σ̂², 10⁻¹²)`
- `SNR = 10 log₁₀(signal_power / noise_power)`

其他单一专家主题现在直接回答当前问题，不再强制使用“我把这个复合问题拆成……”的开场。真正包含多个专家主题时仍会分项表达。

## 六种 SNR 问法验证

| 问题 | Answer Intent | 真实回答要点 |
|---|---|---|
| 信噪比多少？ | VALUE_QUERY | 48 条有效估计；中位数 25.09 dB；范围 10.43–37.70 dB |
| 信噪比怎么算？ | METHOD_QUERY | 输出本工程稳健二阶差分代理方法及完整公式 |
| 为什么这么算？ | CAUSE_QUERY | 解释二阶差分抑制慢趋势、MAD 降低尖峰影响和方法假设 |
| 这个结果可靠吗？ | EVIDENCE_QUERY | `calibrated=False`、48 条证据、`snr_estimates.csv` 溯源和可靠性边界 |
| 哪个时间段信噪比最高？ | COMPARISON_QUERY | `drying_air_flow`，2026-01-01 00:18–00:35，37.70 dB，并列出前 3 |
| 信噪比高说明什么？ | INTERPRETATION_QUERY | 动态方差相对局部噪声更大；不直接等于设备健康或模型可靠 |

六个问题均通过真实浏览器 Agent 对话验证，页面显示的 Answer Intent 和回答内容各不相同。

## 声明式 Scene3D Registry

`frontend/src/data/scene3dRegistry.js` 是三维场景的唯一注册表。每个场景声明场景信息、设备语义节点、结构类型、位置、工艺模块、标准字段绑定和流向。

已注册 `debutanizer_column`、`thermal_power_boiler_long_tail`、`industrial_dryer`、`blast_furnace`、`steel_industry_energy`、`vapor_pressure_soft_sensor`。未知场景进入专用 unknown state，不再回退到高炉模型。

`DigitalTwinView.vue` 使用 `SceneState.data_scene.id` 选择标题、说明、设备分区、工艺流程和三维模型。`project_scene` 只在侧栏作为项目预设背景展示，不覆盖数据场景。

## 3D 交互与资源策略

- 拖动旋转，鼠标滚轮和 `+/-` 按钮缩放，一键复位。
- 点击设备节点后，检查器显示真实标准字段、单位和当前 preview 数值。
- 有真实值的节点显示 live 状态，相关流向启用动画。未配置工程限值时不伪造报警颜色。
- 场景 Registry 以 ES module 单例缓存；组件卸载时取消 animation frame；场景切换时重置选中节点和视角。
- 当前工程唯一 3D Runtime 是 DOM/CSS 3D，不存在 Three.js/Babylon.js 或 GLTF loader。本次未引入第二套引擎，也未伪装成已加载 GLB。后续若统一迁移到 WebGL，引擎可继续消费当前 Registry。

## 浏览器验收

在 `127.0.0.1:8000` Django 与 `127.0.0.1:5176` Vite 上进行真实 Chromium 验收：

1. 项目预设为“钢铁冶金 / 高炉炼铁”，最新 run 数据场景为“工业干燥器”。页面保留两个值并显示“场景不同（正常）”。
2. 标题、工艺说明、设备节点和流程均为工业干燥器，未显示高炉模型。
3. 点击放大成功；点击“回转干燥筒”后显示 `product_temperature = 82.39 degC`。
4. 页面刷新后重新从 latest run 恢复工业干燥器场景。
5. 六个 SNR 问题均通过 live API 与 events polling 完成，没有长期旋转或固定回答。

浏览器验收过程中保存并检查了页面截图，临时测试文件未纳入仓库。

## 测试结果

- Django 全量测试：247 项通过，1 项跳过。
- Answer Intent / Skill Routing 相关测试：37 项通过。
- 前端测试：25 项通过。
- ESLint 与定制 lint：通过。
- Vite production build：通过。

## 修改文件

- `core/skills/answer_intent.py`
- `core/skills/task_understanding.py`
- `core/services/expert_qa.py`
- `core/services/agent_chat.py`
- `core/test_answer_intent.py`
- `frontend/src/data/scene3dRegistry.js`
- `frontend/src/components/SceneModel3D.vue`
- `frontend/src/views/DigitalTwinView.vue`
- `frontend/tests/scene3dRegistry.test.mjs`
- `answer_intent_and_dynamic_3d_report.md`

## 剩余限制

Answer Intent 已接入 TaskSpec 和 SNR 证据回答；其他专家主题已去除单主题固定开场，但还没有全部实现八种专用回答器。当前 3D 是基于现有 DOM/CSS 3D Runtime 的语义设备结构和轻量 LOD，不是 GLTF/GLB 精细模型。
