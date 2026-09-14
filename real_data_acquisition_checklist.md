# 真实数据获取与接收检查表

适用debutanizer_column与industrial_dryer；版本2026-09-14。先查对应正式规范，不改变现有契约。未完成項保留原因/负责人/待补材料，不以测试绿灯替代真实数据执行。

## 来源与文件

- [ ] 来源可信：所有者、发布方、生产线/实验装置、采集系统可追溯。
- [ ] license/授权明确，允许分析；再分发权限单独确认。
- [ ] raw file实际取得并可读；SOURCE_REFERENCE_ONLY不进入执行。
- [ ] SHA-256已记录，文件版本/来源附件一致。
- [ ] 非synthetic冒充；同一来源、过程、设备、时间上下文，没有跨数据集补列。
- [ ] 脱敏、裁剪、缺列、衍生、缩放情况明确。

## 字段与时间

- [ ] 选择对应规范：脱丁烷9 required+1 optional；干燥器7 required+0 optional。
- [ ] required全部真实存在；不是把review字段计成matched。
- [ ] target存在且为原始测量/化验标签，无预测填造。
- [ ] 每列unit及原始计量基准已确认；没有混合单位。
- [ ] equipment、physical location、channel A/B（适用时）已确认。
- [ ] inlet/outlet/reflux/downstream direction（适用时）已确认。
- [ ] timestamp全部可解析、唯一、顺序可恢复，时区明确。
- [ ] sampling周期、证据、丢样/断档、重复处理已记录。
- [ ] 至少150行；不把入口下限当建模充分条件，分区/窗口有效target另验。
- [ ] normalization明确；如缩放，逐字段inverse metadata与处理顺序齐全。
- [ ] 转换均有脚本、source/output hash与manifest，原文件保留。
- [ ] 输入缺失因果处理，输出NaN保留；无跨分区/未来信息填充。

## A14验收

- [ ] 来源/授权人工核验完成（预检工具不认证来源真实性）。
- [ ] 执行tools/precheck_real_dataset.py，保存dataset_precheck.json。
- [ ] final_field_acceptance_gate与单位检查通过。
- [ ] required==matched_required，review/missing/no_equivalent required均0，final_eligibility=ELIGIBLE。
- [ ] SceneContext来自数据场景，输入/target/units与Registry一致。
- [ ] SKILL_MANIFEST_MODE=md，执行现有统一12 Skill Pipeline。
- [ ] 12次executor_invoked回执和同次运行artifact provenance齐全，无blocked/unavailable。
- [ ] 固定train/validation/test协议、冻结模型后单次test，无按test调参。
- [ ] Modeling单独评定PASS/PARTIAL/FAIL；Contract PASS不等于Modeling PASS。

## 本次接收记录（待取得新数据后填写）

场景：____；来源：____；原文件：____；SHA-256：____；授权：____；时间范围：____。
required/matched/review/missing：____；预检：____；run_id：____；12 Skill回执：____；Modeling：____。
未通过原因：____；待补证据：____；接收人/日期：____。

当前基线仍是两个场景Contract FAIL、Pipeline UNAVAILABLE；本表勾选项尚未针对新数据执行。
