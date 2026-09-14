# 脱丁烷塔数据排查结果

结论：UNAVAILABLE。不是 U1/U5/U6/U7 没有别名，也不是项目场景污染；自动识别为 debutanizer_column，四列已映射到相应标准字段，数值合理性检查使其进入 review。

## 本地搜索证据

检索 3541 个 CSV/XLSX/MAT/Parquet/ZIP/metadata/scaler 路径，另核对 56 个 TXT/DAT/HDF/JSONL 路径。CSV header 检索发现 264 个候选（含派生重复文件），按 SHA256 为 73 组；读取错误 0。

使用 rg --files --hidden --no-ignore，包括 Git 忽略的 runtime。只排除 .git、.venv、node_modules 等依赖目录。核对 datasets、演示数据、runtime、reports、docs、training、integrations、acceptance、frontend/public；不存在的目录也记录于搜索清单。查看历史 01_input 原始文件、标准化文件、训练与优化派生产物。

完整清单和逐候选 hash/header：runtime/data_validation/local_data_search.json。合理数据位置内未发现新的物理量脱丁烷源。两个 XLSX 是高炉 Mendeley 工作簿，唯一公开脱丁烷目录只有 README/metadata/prepare 脚本，没有其说明的源 TXT/准备 CSV。

逐层检查 JSON 的 normalization / inverse_transform / inverse_scal / data_min_ / data_max_ / scaler 键，并检索 Python/Markdown 逆归一化说明。仅找到公开脱丁烷 metadata 对“inverse scaling parameters are not published”的明确记录；分类器 LabelEncoder.inverse_transform 是标签还原，不是温度逆变换。

## 实际文件

- source_file: `/Users/komi/Documents/ChatGPT/作品修复/A14/integrations/standardization/training_data/raw_samples/debutanizer_column_raw.csv`
- source_hash: `3679519020df3acf090047019a11c37b0e9f4fefb7747016660a68a7d2d9e629`
- 行数：360；字段 timestamp、U1..U8。
- normalization_method: unknown；inverse_transform_parameters: absent；restored_fields: []。
- U1..U8 数值集中在约 0.13–0.68，当前副本无单位声明。不能仅凭数值落在 0..1 推断 minmax，更不能用模板上下界恢复物理量。
- 公开 metadata 描述 2394 行、派生时间轴、真实采样周期未知、target 已平移 8 个样本；不能把这些事实未经 hash 绑定套到当前 360 行文件。

| 原列 | 标准字段 | 实际 min | 实际 max | 状态 |
|---|---|---:|---:|---|
| U1 | top_temperature | 0.412726 | 0.582863 | review |
| U2 | top_pressure | 0.369992 | 0.537030 | matched |
| U3 | reflux_flow | 0.439676 | 0.677718 | matched |
| U4 | next_process_flow | 0.368004 | 0.596777 | matched |
| U5 | tray6_temperature | 0.427208 | 0.617427 | review |
| U6 | bottom_temperature_a | 0.422416 | 0.595291 | review |
| U7 | bottom_temperature_b | 0.409704 | 0.569357 | review |
| U8 | bottom_butane_content | 0.130506 | 0.249531 | matched |

四个温度字段各有独立未知缩放常数；已有归一化数值不唯一决定真实温度。压力、流量和 target 虽可能在宽范围内 matched，也不证明其单位真实；全链继续阻断。

## 最小配置修复

- TOP_TEMPERATURE 大小写、tray_6_temperature 下划线差异原本就能匹配。
- bottom_temp_a / bottom_temp_b 原本 review，现仅在既有 fields.csv 中增加这两个明确同义别名。没有给 T1/T2/T3 等无设备语义的编号强行指定测点。
- U1..U8、角色、单位、门限均未改动；新增别名后原样本仍缺四个温度字段。
- 离线恢复工具要求 source hash、来源证据、逐字段公式参数和单位；缺一则报错，不自动给 Pipeline 构造恢复值。当前未执行真实数据逆变换。

## 实际运行

run_id: `scene_96612c48c50a`；状态 `unavailable`；耗时 398.57 ms。
12 个节点在标准化门禁后均未调用数值 Executor，没有伪造 SNR、ARX 或模型指标。完整记录见 three_scene_final_runtime_acceptance.json。

脱丁烷完整有效数据链测试明确 skipped，原因是缺合格数据；不把该跳过记成数值 PASS。
