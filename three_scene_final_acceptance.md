# 三场景最终验收

**图中第 2 项当前不能正式判定全部完成。** 场景模块通用 Skill 化的架构贯通维持 PASS；三个场景数值验收仍 PARTIAL，关键缺口是脱丁烷合格物理数据与干燥器动态模型有效性。

| 项目 | 状态 |
|---|---|
| 通用 Skill 架构 | PASS |
| blast_furnace 数值主链 | PARTIAL |
| debutanizer_column 数值主链 | UNAVAILABLE |
| industrial_dryer 数值主链 | PARTIAL |
| 三场景同一 Registry | PASS |
| 三场景同一 Executor | PASS |
| 三场景同一核心算法 | PASS（复用架构；非三场景数值成功） |
| 纯 MD 模式 | PASS |
| 无场景算法复制 | PASS |
| API/前端兼容 | PASS（回归测试与构建） |

本阶段不重构 Runtime、Loader、Planner 或 Registry。架构结论沿用已验收实现，没有把数值 unavailable 改成 success。

## 本次工作

- 搜索当前项目全部合理数据目录及被忽略的历史 artifacts，核对 header、hash、来源和逆归一化信息。完整清单：runtime/data_validation/local_data_search.json。
- 明确四个脱丁烷温度字段为“已识别字段但数值不满足物理契约”，而非识别场景错误。
- 只补 bottom_temp_a/b 两个真实同义缩写；未改角色、单位、字段门限。
- 增加离线显式逆变换工具，缺 source hash/来源证据/逐字段参数/单位则拒绝；当前无可信 metadata，未对验收数据执行逆变换。
- 干燥器补充来源与自由仿真、persistence、多步预测、残差审查及测试隔离回归。未寻找更好的随机种子，没有用测试集调参。
- 高炉保留原始真实数据与 null 边界，仅进行一次最终运行记录的回归；另有自动测试运行不参与结果择优。

## 固定数据实际运行

| 场景 | run_id | Runtime 状态 | 数值结论 | 耗时 ms |
|---|---|---|---|---:|
| debutanizer_column | scene_96612c48c50a | unavailable | UNAVAILABLE | 398.57 |
| industrial_dryer | scene_427eda599cfa | partial | PARTIAL | 686.502 |
| blast_furnace | scene_123d8d4bd1e8 | partial | PARTIAL | 1519.543 |

- 脱丁烷：当前 360 行归一化样本没有可信逆缩放参数，四温度字段仍 review，12 个节点均未数值执行。完整有效数据测试 skipped，不计为 PASS。
- 干燥器：当前最可信的本地候选仍为已有 867 行合成验收集；没有实测来源，严格动态窗口为 0。测试单步 RMSE 0.03980552，高于 persistence 0.02953917，改善 -34.7550%；10 步 RMSE 0.26004044，高于 baseline 0.15071114。自由仿真 R² -0.442265，不能仅凭单步 R² 宣称有效。
- 高炉：主链完成，维持部分 SNR null；保留残差边界，不补值谋求全 PASS。

## 验证结果

- 后端：283 tests，282 通过、1 skipped、0 失败，18.832 秒。涵盖原 275 项及本次新增 8 项。
- skipped：test_debutanizer_full_chain_if_valid_data；缺合格物理数据，不生成替代样本。
- 新增测试：别名匹配、门禁不绕过、逆变换必须有 metadata、条件式完整塔链、干燥器最佳可用源、测试隔离、persistence 对比、三场景最终回归。
- 测试隔离：把 CLEANED_TEST 指向无法解析的文件，ARX 结构选择仍成功且与原训练/验证指标一致，证实选择过程不读测试产物。
- 前端 npm test：30 通过；npm run build：成功，保留既有大包提示。
- git diff --check：通过。API 兼容本次由后端回归验证，未重复浏览器/HTTP 架构审计。

## 修改与交付文件

本阶段代码/配置修改：
- integrations/standardization/standards/scenarios/debutanizer_column/fields.csv：增加两个明确缩写。
- core/services/dataset_evidence.py：离线恢复和审计，未接入自动 Runtime。
- core/test_three_scene_final.py：8 项验证。
- tools/finalize_three_scene_acceptance.py：固定文件、固定配置的真实验收入口。

交付：
- [最终运行 JSON](three_scene_final_runtime_acceptance.json)：来源、hash、run、Context、manifest、executor、逐步指标/证据/警告、停止原因和评价明细。
- [脱丁烷数据报告](debutanizer_data_resolution_report.md)
- [干燥器有效性报告](dryer_data_validation_report.md)
- [剩余缺口](three_scene_final_remaining_gaps.md)
- [脱丁烷数据需求](debutanizer_required_dataset_spec.md)

当前工作区仍包含之前未提交的迁移改动；本阶段未重新实现它们，也未提交或推送 GitHub。
