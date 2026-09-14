# 真实字段Ground Truth
证据标注不使用模型预测生成标签。MATCH同时要求测点与计量含义可确认；仅名称身份对应但缺单位/逆变换的字段为REVIEW_REQUIRED。无文件候选保持未标注，不伪造缺失传感器事实。
|dataset|source|canonical|decision|reason|evidence|
|---|---|---|---|---|---|
| dataset_00 | timestamp | timestamp | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | blast_flow_rate | blast_flow_rate | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | hot_blast_pressure | hot_blast_pressure | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | cold_blast_pressure | cold_blast_pressure | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | cold_blast_temperature | cold_blast_temperature | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | oxygen_flow_rate | oxygen_flow_rate | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | total_pressure_drop | total_pressure_drop | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | upper_pressure_drop | upper_pressure_drop | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | lower_pressure_drop | lower_pressure_drop | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | top_gas_pressure | top_gas_pressure | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | hot_blast_temperature | hot_blast_temperature | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | top_gas_co2 | top_gas_co2 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | top_gas_h2 | top_gas_h2 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | top_gas_temp_1 | top_gas_temp_1 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | top_gas_temp_2 | top_gas_temp_2 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | top_gas_temp_3 | top_gas_temp_3 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | top_gas_temp_4 | top_gas_temp_4 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | peripheral_gas_temp_1 | peripheral_gas_temp_1 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | peripheral_gas_temp_2 | peripheral_gas_temp_2 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | peripheral_gas_temp_3 | peripheral_gas_temp_3 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | peripheral_gas_temp_4 | peripheral_gas_temp_4 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | peripheral_gas_temp_5 | peripheral_gas_temp_5 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | peripheral_gas_temp_6 | peripheral_gas_temp_6 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | peripheral_gas_temp_7 | peripheral_gas_temp_7 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | peripheral_gas_temp_8 | peripheral_gas_temp_8 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | peripheral_gas_temp_9 | peripheral_gas_temp_9 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | peripheral_gas_temp_10 | peripheral_gas_temp_10 | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | ore_coke_ratio | ore_coke_ratio | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | hot_metal_si | hot_metal_si | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | lab_source_timestamp | lab_source_timestamp | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | lab_age_minutes | lab_age_minutes | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_00 | lab_fresh | lab_fresh | MATCH | 实测原始属性说明+固定转换脚本FIELD_MAP，非模型生成标签 | datasets/real_candidates/blast_furnace_mendeley/3_attribute_information.txt + tools/prepare_demo_csv.py + derived_manifest.json |
| dataset_01 | u1 | top_temperature | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_01 | u2 | top_pressure | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_01 | u3 | reflux_flow | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_01 | u4 | next_process_flow | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_01 | u5 | tray6_temperature | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_01 | u6 | bottom_temperature_a | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_01 | u7 | bottom_temperature_b | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_01 | y | bottom_butane_content | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_01 | — | timestamp | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://github.com/Ujjwal-1267/industrial-debutanizer-soft-sensor |
| dataset_02 | u1 | top_temperature | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_02 | u2 | top_pressure | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_02 | u3 | reflux_flow | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_02 | u4 | next_process_flow | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_02 | u5 | tray6_temperature | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_02 | u6 | bottom_temperature_a | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_02 | u7 | bottom_temperature_b | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_02 | y | bottom_butane_content | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_02 | — | timestamp | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://home.isr.uc.pt/~fasouza/debutanizer_fortuna_dataset.zip |
| dataset_03 | U1 | top_temperature | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_03 | U2 | top_pressure | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_03 | U3 | reflux_flow | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_03 | U4 | next_process_flow | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_03 | U5 | tray6_temperature | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_03 | U6 | bottom_temperature_a | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_03 | U7 | bottom_temperature_b | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_03 | U8 | bottom_butane_content | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_03 | — | timestamp | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://github.com/ydycly/DC-dataset |
| dataset_04 | Unnamed: 0 | timestamp | MATCH | 源第二行明确Date /Time；是时间列，不以位置猜测 | https://github.com/LostRunes/debutanizer-model |
| dataset_04 | Feed Flow to DB | next_process_flow | NO_EQUIVALENT | 流入塔的进料不是流向下游的产品 | https://github.com/LostRunes/debutanizer-model |
| dataset_04 | Reboiler o/l Temp | bottom_temperature_b | NO_EQUIVALENT | 不同设备/位置；绝非第二底温 | https://github.com/LostRunes/debutanizer-model |
| dataset_04 | Column top Temp | top_temperature | REVIEW_REQUIRED | 位置明确，但源温标字符编码异常，尚未核验degC | https://github.com/LostRunes/debutanizer-model |
| dataset_04 | Reboiling steam flow | — | NO_EQUIVALENT | 蒸汽加热公用工程不是回流或下游产品 | https://github.com/LostRunes/debutanizer-model |
| dataset_04 | Reflux flow | reflux_flow | MATCH | 源单位TPH，明确回流而非产品流量 | https://github.com/LostRunes/debutanizer-model |
| dataset_04 | Column Top pressure | top_pressure | REVIEW_REQUIRED | 表压kg/cm²g与当前Pa基准/编码需明确 | https://github.com/LostRunes/debutanizer-model |
| dataset_04 | Column bottom temp | bottom_temperature_a | REVIEW_REQUIRED | 只有一个底温，未明确A/B身份，不能复制为两个测点 | https://github.com/LostRunes/debutanizer-model |
| dataset_04 | Control tay temp | tray6_temperature | REVIEW_REQUIRED | 控制板未证明是第六板 | https://github.com/LostRunes/debutanizer-model |
| dataset_04 | C4H6 in DB bottom | bottom_butane_content | NO_EQUIVALENT | C4H6不是丁烷C4H10 | https://github.com/LostRunes/debutanizer-model |
| dataset_04 | C4H8 in DB bottom | bottom_butane_content | NO_EQUIVALENT | C4H8不是丁烷C4H10 | https://github.com/LostRunes/debutanizer-model |
| dataset_04 | — | next_process_flow | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://github.com/LostRunes/debutanizer-model |
| dataset_04 | — | bottom_temperature_b | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://github.com/LostRunes/debutanizer-model |
| dataset_04 | — | bottom_butane_content | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://github.com/LostRunes/debutanizer-model |
| dataset_05 | timestamp | — | REVIEW_REQUIRED | 来源未提供可核验的对应测点/单位；不推断 | integrations/standardization/training_data/raw_samples/debutanizer_column_raw.csv |
| dataset_05 | U1 | top_temperature | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_05 | U2 | top_pressure | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_05 | U3 | reflux_flow | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_05 | U4 | next_process_flow | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_05 | U5 | tray6_temperature | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_05 | U6 | bottom_temperature_a | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_05 | U7 | bottom_temperature_b | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_05 | U8 | bottom_butane_content | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_05 | — | timestamp | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | integrations/standardization/training_data/raw_samples/debutanizer_column_raw.csv |
| dataset_06 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Danny-Taehyun-Kim/debutanizer-hybrid-model |
| dataset_06 | — | top_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Danny-Taehyun-Kim/debutanizer-hybrid-model |
| dataset_06 | — | top_pressure | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Danny-Taehyun-Kim/debutanizer-hybrid-model |
| dataset_06 | — | reflux_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Danny-Taehyun-Kim/debutanizer-hybrid-model |
| dataset_06 | — | next_process_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Danny-Taehyun-Kim/debutanizer-hybrid-model |
| dataset_06 | — | tray6_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Danny-Taehyun-Kim/debutanizer-hybrid-model |
| dataset_06 | — | bottom_temperature_a | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Danny-Taehyun-Kim/debutanizer-hybrid-model |
| dataset_06 | — | bottom_temperature_b | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Danny-Taehyun-Kim/debutanizer-hybrid-model |
| dataset_06 | — | bottom_butane_content | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Danny-Taehyun-Kim/debutanizer-hybrid-model |
| dataset_07 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2076-3417/11/24/11790 |
| dataset_07 | — | top_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2076-3417/11/24/11790 |
| dataset_07 | — | top_pressure | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2076-3417/11/24/11790 |
| dataset_07 | — | reflux_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2076-3417/11/24/11790 |
| dataset_07 | — | next_process_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2076-3417/11/24/11790 |
| dataset_07 | — | tray6_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2076-3417/11/24/11790 |
| dataset_07 | — | bottom_temperature_a | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2076-3417/11/24/11790 |
| dataset_07 | — | bottom_temperature_b | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2076-3417/11/24/11790 |
| dataset_07 | — | bottom_butane_content | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2076-3417/11/24/11790 |
| dataset_08 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S0009250925004269 |
| dataset_08 | — | top_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S0009250925004269 |
| dataset_08 | — | top_pressure | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S0009250925004269 |
| dataset_08 | — | reflux_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S0009250925004269 |
| dataset_08 | — | next_process_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S0009250925004269 |
| dataset_08 | — | tray6_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S0009250925004269 |
| dataset_08 | — | bottom_temperature_a | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S0009250925004269 |
| dataset_08 | — | bottom_temperature_b | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S0009250925004269 |
| dataset_08 | — | bottom_butane_content | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S0009250925004269 |
| dataset_09 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Dharmesh-47/Soft-Sensor-for-Debutanizer-Distillation-Column |
| dataset_09 | — | top_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Dharmesh-47/Soft-Sensor-for-Debutanizer-Distillation-Column |
| dataset_09 | — | top_pressure | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Dharmesh-47/Soft-Sensor-for-Debutanizer-Distillation-Column |
| dataset_09 | — | reflux_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Dharmesh-47/Soft-Sensor-for-Debutanizer-Distillation-Column |
| dataset_09 | — | next_process_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Dharmesh-47/Soft-Sensor-for-Debutanizer-Distillation-Column |
| dataset_09 | — | tray6_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Dharmesh-47/Soft-Sensor-for-Debutanizer-Distillation-Column |
| dataset_09 | — | bottom_temperature_a | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Dharmesh-47/Soft-Sensor-for-Debutanizer-Distillation-Column |
| dataset_09 | — | bottom_temperature_b | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Dharmesh-47/Soft-Sensor-for-Debutanizer-Distillation-Column |
| dataset_09 | — | bottom_butane_content | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://github.com/Dharmesh-47/Soft-Sensor-for-Debutanizer-Distillation-Column |
| dataset_10 | sample_index | timestamp | REVIEW_REQUIRED | 来源确认10秒有序采样；无日历起点，当前墙钟接入尚需显式转换 | runtime/data_validation/public_candidates/daisy_dryer_description.txt |
| dataset_10 | fuel_flow | — | NO_EQUIVALENT | 燃料流量不是热风温度 | runtime/data_validation/public_candidates/daisy_dryer_description.txt |
| dataset_10 | exhaust_fan_speed | drying_air_flow | NO_EQUIVALENT | 转速不是标准体积风量 | runtime/data_validation/public_candidates/daisy_dryer_description.txt |
| dataset_10 | raw_material_flow | wet_feed_rate | REVIEW_REQUIRED | 原料流量意义接近，但单位和偏置缺失 | runtime/data_validation/public_candidates/daisy_dryer_description.txt |
| dataset_10 | dry_bulb_temperature | hot_air_temperature | REVIEW_REQUIRED | 干球测温位置不明，不能当入口或出口温度 | runtime/data_validation/public_candidates/daisy_dryer_description.txt |
| dataset_10 | wet_bulb_temperature | exhaust_humidity | NO_EQUIVALENT | 湿球温度不是相对湿度 | runtime/data_validation/public_candidates/daisy_dryer_description.txt |
| dataset_10 | raw_material_moisture | product_moisture | NO_EQUIVALENT | 原料水分不是出口产品水分；负值无逆变换说明 | runtime/data_validation/public_candidates/daisy_dryer_description.txt |
| dataset_10 | — | drying_air_flow | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://homes.esat.kuleuven.be/~tokka/daisydata.html |
| dataset_10 | — | product_moisture | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://homes.esat.kuleuven.be/~tokka/daisydata.html |
| dataset_10 | — | product_temperature | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://homes.esat.kuleuven.be/~tokka/daisydata.html |
| dataset_10 | — | exhaust_humidity | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://homes.esat.kuleuven.be/~tokka/daisydata.html |
| dataset_11 | A | timestamp | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | B | — | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | C | — | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | D | — | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | E | — | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | F | — | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | G | — | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | H | — | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | I | — | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | J | — | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | K | — | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | L | — | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | M | — | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | N | — | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | O | — | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | P | — | REVIEW_REQUIRED | 来源XLSX相对时间/多组温度试次统计；没有入口风量、连续进料、排气湿度和时序产品水分 | runtime/data_validation/public_candidates/coffee.xlsx |
| dataset_11 | — | hot_air_temperature | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://zenodo.org/records/16729583 |
| dataset_11 | — | drying_air_flow | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://zenodo.org/records/16729583 |
| dataset_11 | — | wet_feed_rate | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://zenodo.org/records/16729583 |
| dataset_11 | — | product_moisture | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://zenodo.org/records/16729583 |
| dataset_11 | — | product_temperature | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://zenodo.org/records/16729583 |
| dataset_11 | — | exhaust_humidity | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://zenodo.org/records/16729583 |
| dataset_12 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://ieee-dataport.org/documents/industrial-drying-filter-media-moisture-content-prediction |
| dataset_12 | — | hot_air_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://ieee-dataport.org/documents/industrial-drying-filter-media-moisture-content-prediction |
| dataset_12 | — | drying_air_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://ieee-dataport.org/documents/industrial-drying-filter-media-moisture-content-prediction |
| dataset_12 | — | wet_feed_rate | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://ieee-dataport.org/documents/industrial-drying-filter-media-moisture-content-prediction |
| dataset_12 | — | product_moisture | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://ieee-dataport.org/documents/industrial-drying-filter-media-moisture-content-prediction |
| dataset_12 | — | product_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://ieee-dataport.org/documents/industrial-drying-filter-media-moisture-content-prediction |
| dataset_12 | — | exhaust_humidity | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://ieee-dataport.org/documents/industrial-drying-filter-media-moisture-content-prediction |
| dataset_13 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/935258dxnt/1 |
| dataset_13 | — | hot_air_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/935258dxnt/1 |
| dataset_13 | — | drying_air_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/935258dxnt/1 |
| dataset_13 | — | wet_feed_rate | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/935258dxnt/1 |
| dataset_13 | — | product_moisture | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/935258dxnt/1 |
| dataset_13 | — | product_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/935258dxnt/1 |
| dataset_13 | — | exhaust_humidity | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/935258dxnt/1 |
| dataset_14 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/hc3hftr4sm/2 |
| dataset_14 | — | hot_air_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/hc3hftr4sm/2 |
| dataset_14 | — | drying_air_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/hc3hftr4sm/2 |
| dataset_14 | — | wet_feed_rate | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/hc3hftr4sm/2 |
| dataset_14 | — | product_moisture | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/hc3hftr4sm/2 |
| dataset_14 | — | product_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/hc3hftr4sm/2 |
| dataset_14 | — | exhaust_humidity | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/hc3hftr4sm/2 |
| dataset_15 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S2352340920312178 |
| dataset_15 | — | hot_air_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S2352340920312178 |
| dataset_15 | — | drying_air_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S2352340920312178 |
| dataset_15 | — | wet_feed_rate | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S2352340920312178 |
| dataset_15 | — | product_moisture | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S2352340920312178 |
| dataset_15 | — | product_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S2352340920312178 |
| dataset_15 | — | exhaust_humidity | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.sciencedirect.com/science/article/pii/S2352340920312178 |
| dataset_16 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://zenodo.org/records/18630186 |
| dataset_16 | — | hot_air_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://zenodo.org/records/18630186 |
| dataset_16 | — | drying_air_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://zenodo.org/records/18630186 |
| dataset_16 | — | wet_feed_rate | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://zenodo.org/records/18630186 |
| dataset_16 | — | product_moisture | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://zenodo.org/records/18630186 |
| dataset_16 | — | product_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://zenodo.org/records/18630186 |
| dataset_16 | — | exhaust_humidity | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://zenodo.org/records/18630186 |
| dataset_17 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://research.wur.nl/en/datasets/models-and-dataset-underlying-the-publication-towards-industrial-/ |
| dataset_17 | — | hot_air_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://research.wur.nl/en/datasets/models-and-dataset-underlying-the-publication-towards-industrial-/ |
| dataset_17 | — | drying_air_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://research.wur.nl/en/datasets/models-and-dataset-underlying-the-publication-towards-industrial-/ |
| dataset_17 | — | wet_feed_rate | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://research.wur.nl/en/datasets/models-and-dataset-underlying-the-publication-towards-industrial-/ |
| dataset_17 | — | product_moisture | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://research.wur.nl/en/datasets/models-and-dataset-underlying-the-publication-towards-industrial-/ |
| dataset_17 | — | product_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://research.wur.nl/en/datasets/models-and-dataset-underlying-the-publication-towards-industrial-/ |
| dataset_17 | — | exhaust_humidity | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://research.wur.nl/en/datasets/models-and-dataset-underlying-the-publication-towards-industrial-/ |
| dataset_18 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2227-9717/14/5/871 |
| dataset_18 | — | hot_air_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2227-9717/14/5/871 |
| dataset_18 | — | drying_air_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2227-9717/14/5/871 |
| dataset_18 | — | wet_feed_rate | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2227-9717/14/5/871 |
| dataset_18 | — | product_moisture | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2227-9717/14/5/871 |
| dataset_18 | — | product_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2227-9717/14/5/871 |
| dataset_18 | — | exhaust_humidity | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.mdpi.com/2227-9717/14/5/871 |
| dataset_19 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.tandfonline.com/doi/full/10.1080/07373937.2025.2486103 |
| dataset_19 | — | hot_air_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.tandfonline.com/doi/full/10.1080/07373937.2025.2486103 |
| dataset_19 | — | drying_air_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.tandfonline.com/doi/full/10.1080/07373937.2025.2486103 |
| dataset_19 | — | wet_feed_rate | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.tandfonline.com/doi/full/10.1080/07373937.2025.2486103 |
| dataset_19 | — | product_moisture | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.tandfonline.com/doi/full/10.1080/07373937.2025.2486103 |
| dataset_19 | — | product_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.tandfonline.com/doi/full/10.1080/07373937.2025.2486103 |
| dataset_19 | — | exhaust_humidity | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://www.tandfonline.com/doi/full/10.1080/07373937.2025.2486103 |
| dataset_20 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://juti.if.its.ac.id/index.php/juti/article/view/1599 |
| dataset_20 | — | hot_air_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://juti.if.its.ac.id/index.php/juti/article/view/1599 |
| dataset_20 | — | drying_air_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://juti.if.its.ac.id/index.php/juti/article/view/1599 |
| dataset_20 | — | wet_feed_rate | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://juti.if.its.ac.id/index.php/juti/article/view/1599 |
| dataset_20 | — | product_moisture | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://juti.if.its.ac.id/index.php/juti/article/view/1599 |
| dataset_20 | — | product_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://juti.if.its.ac.id/index.php/juti/article/view/1599 |
| dataset_20 | — | exhaust_humidity | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://juti.if.its.ac.id/index.php/juti/article/view/1599 |
| dataset_21 | 采集时间 | — | REVIEW_REQUIRED | 合成开发样本，禁止作为真实字段验收真值 | 演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv |
| dataset_21 | 入口热风温度 | — | REVIEW_REQUIRED | 合成开发样本，禁止作为真实字段验收真值 | 演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv |
| dataset_21 | 热风流量 | — | REVIEW_REQUIRED | 合成开发样本，禁止作为真实字段验收真值 | 演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv |
| dataset_21 | 给料量 | — | REVIEW_REQUIRED | 合成开发样本，禁止作为真实字段验收真值 | 演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv |
| dataset_21 | 产品水分 | — | REVIEW_REQUIRED | 合成开发样本，禁止作为真实字段验收真值 | 演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv |
| dataset_21 | 物料出口温度 | — | REVIEW_REQUIRED | 合成开发样本，禁止作为真实字段验收真值 | 演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv |
| dataset_21 | 尾气湿度 | — | REVIEW_REQUIRED | 合成开发样本，禁止作为真实字段验收真值 | 演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv |
| dataset_21 | — | timestamp | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | 演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv |
| dataset_21 | — | hot_air_temperature | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | 演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv |
| dataset_21 | — | drying_air_flow | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | 演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv |
| dataset_21 | — | wet_feed_rate | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | 演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv |
| dataset_21 | — | product_moisture | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | 演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv |
| dataset_21 | — | product_temperature | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | 演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv |
| dataset_21 | — | exhaust_humidity | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | 演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv |
| dataset_22 | 采集时间 | — | REVIEW_REQUIRED | 合成开发样本，禁止作为真实字段验收真值 | integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv |
| dataset_22 | 入口热风温度 | — | REVIEW_REQUIRED | 合成开发样本，禁止作为真实字段验收真值 | integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv |
| dataset_22 | 热风流量 | — | REVIEW_REQUIRED | 合成开发样本，禁止作为真实字段验收真值 | integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv |
| dataset_22 | 给料量 | — | REVIEW_REQUIRED | 合成开发样本，禁止作为真实字段验收真值 | integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv |
| dataset_22 | 产品水分 | — | REVIEW_REQUIRED | 合成开发样本，禁止作为真实字段验收真值 | integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv |
| dataset_22 | 物料出口温度 | — | REVIEW_REQUIRED | 合成开发样本，禁止作为真实字段验收真值 | integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv |
| dataset_22 | 尾气湿度 | — | REVIEW_REQUIRED | 合成开发样本，禁止作为真实字段验收真值 | integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv |
| dataset_22 | — | timestamp | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv |
| dataset_22 | — | hot_air_temperature | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv |
| dataset_22 | — | drying_air_flow | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv |
| dataset_22 | — | wet_feed_rate | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv |
| dataset_22 | — | product_moisture | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv |
| dataset_22 | — | product_temperature | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv |
| dataset_22 | — | exhaust_humidity | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv |
| dataset_23 | u1 | top_temperature | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_23 | u2 | top_pressure | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_23 | u3 | reflux_flow | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_23 | u4 | next_process_flow | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_23 | u5 | tray6_temperature | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_23 | u6 | bottom_temperature_a | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_23 | u7 | bottom_temperature_b | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_23 | y | bottom_butane_content | REVIEW_REQUIRED | 命名对应来自已声明Fortuna字段字典；源数值归一化，缺逐字段物理inverse元数据 | datasets/public/debutanizer/dataset_metadata.json + datasets/public/debutanizer/README.md |
| dataset_23 | — | timestamp | MISSING_STANDARD_FIELD | 完整已读字段表未发现可信对应测点 | https://github.com/StevenShaw98/Debutanizer-Column-Process |
| dataset_24 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://pmc.ncbi.nlm.nih.gov/articles/PMC8228335/ |
| dataset_24 | — | top_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://pmc.ncbi.nlm.nih.gov/articles/PMC8228335/ |
| dataset_24 | — | top_pressure | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://pmc.ncbi.nlm.nih.gov/articles/PMC8228335/ |
| dataset_24 | — | reflux_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://pmc.ncbi.nlm.nih.gov/articles/PMC8228335/ |
| dataset_24 | — | next_process_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://pmc.ncbi.nlm.nih.gov/articles/PMC8228335/ |
| dataset_24 | — | tray6_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://pmc.ncbi.nlm.nih.gov/articles/PMC8228335/ |
| dataset_24 | — | bottom_temperature_a | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://pmc.ncbi.nlm.nih.gov/articles/PMC8228335/ |
| dataset_24 | — | bottom_temperature_b | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://pmc.ncbi.nlm.nih.gov/articles/PMC8228335/ |
| dataset_24 | — | bottom_butane_content | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://pmc.ncbi.nlm.nih.gov/articles/PMC8228335/ |
| dataset_25 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://utpedia.utp.edu.my/id/eprint/6680/ |
| dataset_25 | — | top_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://utpedia.utp.edu.my/id/eprint/6680/ |
| dataset_25 | — | top_pressure | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://utpedia.utp.edu.my/id/eprint/6680/ |
| dataset_25 | — | reflux_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://utpedia.utp.edu.my/id/eprint/6680/ |
| dataset_25 | — | next_process_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://utpedia.utp.edu.my/id/eprint/6680/ |
| dataset_25 | — | tray6_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://utpedia.utp.edu.my/id/eprint/6680/ |
| dataset_25 | — | bottom_temperature_a | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://utpedia.utp.edu.my/id/eprint/6680/ |
| dataset_25 | — | bottom_temperature_b | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://utpedia.utp.edu.my/id/eprint/6680/ |
| dataset_25 | — | bottom_butane_content | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://utpedia.utp.edu.my/id/eprint/6680/ |
| dataset_26 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/v3bvdmccmm/1 |
| dataset_26 | — | hot_air_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/v3bvdmccmm/1 |
| dataset_26 | — | drying_air_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/v3bvdmccmm/1 |
| dataset_26 | — | wet_feed_rate | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/v3bvdmccmm/1 |
| dataset_26 | — | product_moisture | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/v3bvdmccmm/1 |
| dataset_26 | — | product_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/v3bvdmccmm/1 |
| dataset_26 | — | exhaust_humidity | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/v3bvdmccmm/1 |
| dataset_27 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/cgjpm86mwg/1 |
| dataset_27 | — | hot_air_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/cgjpm86mwg/1 |
| dataset_27 | — | drying_air_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/cgjpm86mwg/1 |
| dataset_27 | — | wet_feed_rate | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/cgjpm86mwg/1 |
| dataset_27 | — | product_moisture | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/cgjpm86mwg/1 |
| dataset_27 | — | product_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/cgjpm86mwg/1 |
| dataset_27 | — | exhaust_humidity | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/cgjpm86mwg/1 |
| dataset_28 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi%3A10.57745%2F0BYMZL |
| dataset_28 | — | hot_air_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi%3A10.57745%2F0BYMZL |
| dataset_28 | — | drying_air_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi%3A10.57745%2F0BYMZL |
| dataset_28 | — | wet_feed_rate | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi%3A10.57745%2F0BYMZL |
| dataset_28 | — | product_moisture | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi%3A10.57745%2F0BYMZL |
| dataset_28 | — | product_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi%3A10.57745%2F0BYMZL |
| dataset_28 | — | exhaust_humidity | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi%3A10.57745%2F0BYMZL |
| dataset_29 | — | timestamp | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/yxwn9g2n6s/1 |
| dataset_29 | — | hot_air_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/yxwn9g2n6s/1 |
| dataset_29 | — | drying_air_flow | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/yxwn9g2n6s/1 |
| dataset_29 | — | wet_feed_rate | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/yxwn9g2n6s/1 |
| dataset_29 | — | product_moisture | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/yxwn9g2n6s/1 |
| dataset_29 | — | product_temperature | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/yxwn9g2n6s/1 |
| dataset_29 | — | exhaust_humidity | REVIEW_REQUIRED | 未取得原文件，不能断言物理传感器不存在；获取源文件前待复核 | https://data.mendeley.com/datasets/yxwn9g2n6s/1 |