# 脱丁烷塔 Pipeline 专项验收

Pipeline：UNAVAILABLE。Modeling：NOT_EXECUTED。图中第2项：PARTIAL。

本次读取完整契约并复查本地CSV，记录19份候选文件、0扫描错误；同时继承上一轮MAT/TXT等公开源核验。没有可信逆缩放元数据，也没有满足当前测点和目标定义的物理数据。未删除必需字段，未生成合成替代，未执行逆变换。

## 固定数据真实请求
run_id：`scene_07f8c41f4d12`；skill_run_id：`skillrun_bb5ec63bde77`。
dataset_ref：`/Users/komi/Documents/ChatGPT/作品修复/A14/integrations/standardization/training_data/raw_samples/debutanizer_column_raw.csv`；SHA256：`3679519020df3acf090047019a11c37b0e9f4fefb7747016660a68a7d2d9e629`。
SKILL_MANIFEST_MODE=md；elapsed_ms：338.186。
阻断原因：缺少必须的标准字段：bottom_temperature_a, bottom_temperature_b, top_temperature, tray6_temperature。

本次实际运行了数据标准化和MD规划/门禁；以下是12个节点的拒绝回执，**不是12个数值Executor执行成功**。SceneContext虽已从模板构建，也不证明数据符合契约。

|Skill|status|executor_invoked|
|---|---|---|
|time_axis_alignment_resampler|blocked|False|
|missing_anomaly_cleaner|blocked|False|
|signal_noise_ratio_estimator|blocked|False|
|steady_transient_state_detector|blocked|False|
|high_snr_dynamic_segment_extractor|blocked|False|
|segment_quality_scorer_ranker|blocked|False|
|time_delay_estimator_compensator|blocked|False|
|collinearity_detector_reducer|blocked|False|
|modeling_dataset_assembler|blocked|False|
|arx_structure_order_selector|blocked|False|
|system_identification_trainer|blocked|False|
|model_diagnostics_evaluator|blocked|False|

完整SceneContext、manifest路径、Executor模块、参数、metrics、warnings、artifacts见同名JSON。被阻断的metrics为空，不伪造baseline、稳定性、多步、仿真或残差结果。

## 新发现：跨测点误匹配
`core/test_debutanizer_contract.py::test_debutanizer_alias_mapping` 的明确同义列测试通过，但反例失败：`Reboiler o/l Temp → bottom_temperature_b`（confidence 0.879）；`Feed Flow to DB → next_process_flow`（0.883）。两项均为 trained_model_auto。位置在 `integrations/standardization/standard_agent/engine.py:270` 的模型候选路径，不是fields.csv明确alias。不能因为数值落在范围内就确认物理等价，因此未将LostRunes候选送入数值运行。

此次不修改共享字段模型/匹配算法，也不添加假alias。独立失败测试保留，避免把当前行为误写成安全保证。

## 测试与范围
7项专项测试：5通过、1失败、1跳过。失败是上述真实测点误匹配；跳过的是12节点完整数值验收（缺合格数据）。测试中legacy pipeline被设为调用即报错，实际0次调用；这只证明阻断路径未fallback，不证明完整执行路径已成功。

新增代码仅 `core/test_debutanizer_contract.py`；交付五份专项报告/JSON及本次runtime证据。未改Runtime、Loader、Registry、Planner、SceneContext、其他场景或算法。old_contract=new_contract。

## 下一步所需证据
需要真实的两处底温、第六塔板、塔顶温度/压力、回流及下游流量、丁烷目标与时间；或可信源方逐字段逆缩放和采样元数据。模板默认60秒不用于补造来源时间。缺失数据不能由修改required替代。