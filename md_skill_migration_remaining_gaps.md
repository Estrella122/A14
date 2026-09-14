# 尚未迁移及边界

## 未完成范围

1. 第一阶段四个核心算法 Skill 已迁移；其余 26 个业务 Skill 仍由旧 catalog 注册。不要把“可以读取其旧 SKILL.md”视为已经迁移。
2. 用户列出的第二批十二项尚未迁移：csv_asset_manager、semantic_field_unit_standardizer、time_axis_alignment_resampler、missing_anomaly_cleaner、steady_transient_state_detector、high_snr_dynamic_segment_extractor、segment_quality_scorer_ranker、modeling_dataset_assembler、system_identification_trainer、multi_model_benchmark、model_diagnostics_evaluator、closed_loop_preprocessing_optimizer。
3. 原 execution_plan.GROUP_SKILLS、contracts.SKILL_CONTRACTS 及 industrial-analysis capability registry 仍负责 legacy 工作流。完整 pipeline 和混合已迁移/未迁移请求按原流程执行，manifest_fallback 会说明原因。尚未实现同一复合请求内任意 legacy 节点与 MD 节点的无重复混合 DAG。
4. 四个 Skill 的 `legacy_handler` 只用于旧流程读取历史结果，不用于 MD 独立算法选择。旧流程执行记录明确区分 executed、evidence_only、blocked。
5. 虽然纯 md 模式不使用 catalog 注册定义，Python 兼容模块仍可能被导入；本次没有物理删除那些导入或旧文件。

## evidence read 与计算

CSV 资产管理、最终产物导出、证据审计主要读取现有文件/引用，不能宣称重跑了业务算法。动态段评分、数据集组装、多模型对比等可能由共享分段/建模 stage 一次生成，再被多个展示 Skill 读取；迁移时不能给每个展示项重新跑一遍共享 stage。

第二批应按 stage 的实际计算边界逐个迁移。read manifest 必须明确读取 validated_pipeline_bundle；共享 stage 的多个 Skill 需要记录 executed/reused，不能虚报每个子能力均有独立算法调用。

## 模型与证据边界

- MD 语义匹配是确定性文本评分，不是 embedding/LLM 语义模型；短句、多义表达和复杂跨领域任务仍需要扩充实测样本。
- SNR 对本次 CLEANED_TRAIN 整个有序序列逐字段估计，并非旧分窗 SNR 的中位数。这是相同 snr_details 算法在明确输入范围上的新执行，不能混为一项指标。
- 时滞补偿继续复用原 TimeDelayCapabilityExecutor；本次不修改其底层统计/补偿语义。
- ARX 完成结构选择，不代表生产可用；当前 HTTP SNR 验收用真实 xinan 上传产物，四项联合成功验收使用已有“工业干燥器…合成验收数据.csv”的运行产物，后者不是工厂实测数据。
- 输入 artifact 的持久化和历史有效性仍沿用现有 RuntimeArtifactResolver。manifest hash 已绑定计划；完整跨版本缓存/重算策略尚未新增。
- manifest validation 允许未来 read/orchestration/unavailable 模式，第一阶段的四项均为 execute；这不等于第二批已完成。

## 闭环优化

只增加 SkillRoundRecord 接口。现有 optimizer 内部迭代没有重写为 Supervisor 逐轮调用 MD Skill；停止条件、参数变更授权、缓存复用和跨轮依赖尚待后续实现。

## 运行与前端

保留所有现有 API，实测本地 HTTP + live polling。前端单元测试与构建通过；本次没有进行完整浏览器手动点击验收，不把 HTTP 验证写成浏览器验收。生产部署仍需安装新增 PyYAML 并重启服务。没有修改场景识别、字段映射或 3D 资产。
