# Agent-level acceptance report

任务 `20260905_143109_46b18f3b`，从 `/api/agent/chat/` 真实视图入口执行11个场景，全部通过。

路由使用离线多语言语义向量和通用metadata术语覆盖率，匹配when_to_use及描述，按contract绑定输入；没有分析类型关键词分支。

所有场景：最终报告读取为0；污染旧摘要后，选择、结构化结果与回答不变；原始数据与流水线已有产物哈希不变。缺数据场景只在内存中移除预测产物目录项，没有删除文件。

## missing：检查煤气流量的缺失情况

选择：field_missing

状态码：None

事实 / 计算结果：
- gas_flow：标准化清洗前 4320 行，缺失 0 个（0.00%）；原始字段 gas_flow 的 4320 行中缺失 0 个

不确定项 / 所需输入：
- 原始/标准化空值与重采样空档是不同口径；此处不把清洗后的零空值当作原始完整。

数据证据：
- 02_standardization/standardized.csv（4320；SHA256 fa5385c50b0b）
- 01_input/source.csv（4320；SHA256 32e735072fbb）

选择依据：[[{"need": "缺失情况", "matched_when_to_use": "字段存在性及缺失统计", "similarity": 0.8137, "metadata_hash": "49434e218f439a982d008ec2c6c59c1aa43fcf254a16e399ee159d20940ac3df", "required_inputs": ["standardized_csv", "source_csv"], "output_contract": "missing_count,missing_rate,absent_fields"}]]

Receipt：8fa9c16845d34480abc470ef6d490b0d

## anomaly：检查煤气流量有哪些异常点

选择：anomaly_analysis

状态码：None

事实 / 计算结果：
- gas_flow：规则标记异常 36/4320 个（0.83%）

不确定项 / 所需输入：
- 异常为现有物理边界、阶跃、局部MAD规则命中，不等于已确认设备故障；未保存或替换修复后的数据。
- 阶跃阈值作用于相邻记录；记录间隔变化可能影响解释。

数据证据：
- 02_standardization/standardized.csv（4320；SHA256 fa5385c50b0b）

选择依据：[[{"need": "有哪些异常点", "matched_when_to_use": "异常点规则分析", "similarity": 0.74135, "metadata_hash": "9dc22881c7199a63ed9bc35827c2589e90d75282f74465c277f8fc9139e55981", "required_inputs": ["standardized_csv", "variable_spec"], "output_contract": "anomaly_count,anomaly_rate,examples"}]]

Receipt：4d064a33675742da85804a544964c0fd

## lag_correlation：分析煤气流量与出炉温度的时滞和相关性

选择：time_delay、correlation

状态码：None

事实 / 计算结果：
- gas_flow → slab_discharge_temp：统计时滞 17 个采样点（170 秒），相关系数 0.9849
- gas_flow / slab_discharge_temp：Pearson r=0.8175，共同样本 2592

不确定项 / 所需输入：
- 最大绝对相关对应统计时滞，不证明因果；负值表示输出领先输入。
- 相关性不等于因果；缺失值按变量对剔除，各对样本数可能不同。

数据证据：
- 03_cleaning/train.csv（2592；SHA256 9c28f9944ca1）
- 03_cleaning/evaluation_protocol.json（JSON；SHA256 2d4c519fce57）

选择依据：[[{"need": "时滞", "matched_when_to_use": "分段时滞估计", "similarity": 0.80945, "metadata_hash": "2d74dd2140b32090ae9c3752aed7783ae0c7414b9764dd00dbf67b4c4f903b25", "required_inputs": ["training_csv", "evaluation_json", "fields", "output"], "output_contract": "delay_samples,delay_seconds,correlation"}], [{"need": "相关性", "matched_when_to_use": "Pearson相关性分析", "similarity": 0.83058, "metadata_hash": "854674d398fea28beb4b892be98d9e91baa8aa44b959be829b323aca40417567", "required_inputs": ["training_csv"], "output_contract": "pairs,correlation,n_samples"}]]

Receipt：b7294ec97c8c461188fd9121ce981dd3

## model_error：分析当前模型的预测误差

选择：model_error

状态码：None

事实 / 计算结果：
- slab_discharge_temp：最终测试 646 个有效预测，R²=0.9999，RMSE=0.3663，MAE=0.2835，平均残差=-0.0275
- 较大误差位置 2026-08-01 19:00:00：实测 1203.7459，预测 1202.2776，残差 1.4684
- 较大误差位置 2026-08-01 19:03:40：实测 1194.6329，预测 1195.9925，残差 -1.3596
- 较大误差位置 2026-08-01 19:08:00：实测 1150.4458，预测 1151.6385，残差 -1.1927

不确定项 / 所需输入：
- 使用历史实测输出的单步预测误差，不能推断自由滚动预测或现场控制效果。
- 残差自相关按有效预测记录顺序计算，lag不是跨时间空档的物理秒数。

数据证据：
- 04_modeling/03_system_identification/final_test_predictions.csv（646；SHA256 ee0952a51890）

选择依据：[[{"need": "模型预测误差", "matched_when_to_use": "评估模型预测误差、残差和拟合效果", "similarity": 0.94639, "metadata_hash": "1df3ff735cd78d468d7ef726ffce187c51a00ebb0ded75bab48956cb306329f8", "required_inputs": ["test_predictions_csv"], "output_contract": "metrics,bias,worst,residual_autocorrelation"}]]

Receipt：1f8f2d5705c240d883fdb6b2566d5537

## combined_original：综合检查煤气流量的缺失、异常和当前模型误差

选择：field_missing、anomaly_analysis、model_error

状态码：None

事实 / 计算结果：
- gas_flow：标准化清洗前 4320 行，缺失 0 个（0.00%）；原始字段 gas_flow 的 4320 行中缺失 0 个
- gas_flow：规则标记异常 36/4320 个（0.83%）
- slab_discharge_temp：最终测试 646 个有效预测，R²=0.9999，RMSE=0.3663，MAE=0.2835，平均残差=-0.0275
- 较大误差位置 2026-08-01 19:00:00：实测 1203.7459，预测 1202.2776，残差 1.4684
- 较大误差位置 2026-08-01 19:03:40：实测 1194.6329，预测 1195.9925，残差 -1.3596
- 较大误差位置 2026-08-01 19:08:00：实测 1150.4458，预测 1151.6385，残差 -1.1927

推断：
- 上述分析来自同一任务；同时出现缺失、异常或模型误差不能单独证明它们之间的因果关系。

不确定项 / 所需输入：
- 原始/标准化空值与重采样空档是不同口径；此处不把清洗后的零空值当作原始完整。
- 异常为现有物理边界、阶跃、局部MAD规则命中，不等于已确认设备故障；未保存或替换修复后的数据。
- 阶跃阈值作用于相邻记录；记录间隔变化可能影响解释。
- 使用历史实测输出的单步预测误差，不能推断自由滚动预测或现场控制效果。
- 残差自相关按有效预测记录顺序计算，lag不是跨时间空档的物理秒数。

数据证据：
- 02_standardization/standardized.csv（4320；SHA256 fa5385c50b0b）
- 01_input/source.csv（4320；SHA256 32e735072fbb）
- 04_modeling/03_system_identification/final_test_predictions.csv（646；SHA256 ee0952a51890）

选择依据：[[{"need": "缺失", "matched_when_to_use": "字段存在性及缺失统计", "similarity": 0.77342, "metadata_hash": "49434e218f439a982d008ec2c6c59c1aa43fcf254a16e399ee159d20940ac3df", "required_inputs": ["standardized_csv", "source_csv"], "output_contract": "missing_count,missing_rate,absent_fields"}], [{"need": "异常", "matched_when_to_use": "异常点规则分析", "similarity": 0.75565, "metadata_hash": "9dc22881c7199a63ed9bc35827c2589e90d75282f74465c277f8fc9139e55981", "required_inputs": ["standardized_csv", "variable_spec"], "output_contract": "anomaly_count,anomaly_rate,examples"}], [{"need": "模型误差", "matched_when_to_use": "评估模型预测误差、残差和拟合效果", "similarity": 0.62929, "metadata_hash": "1df3ff735cd78d468d7ef726ffce187c51a00ebb0ded75bab48956cb306329f8", "required_inputs": ["test_predictions_csv"], "output_contract": "metrics,bias,worst,residual_autocorrelation"}]]

Receipt：1912b85598b74187824a13bc9287bb47

## collinearity：分析煤气流量和空气流量是否共线

选择：collinearity

状态码：None

事实 / 计算结果：
- air_flow：VIF=2.613
- gas_flow：VIF=2.613

推断：
- 变量保留/删除是现有VIF和相关性规则的建议，尚未据此重训或修改模型。

数据证据：
- 03_cleaning/train.csv（2592；SHA256 9c28f9944ca1）

选择依据：[[{"need": "是否共线", "matched_when_to_use": "共线性及变量建议", "similarity": 0.65579, "metadata_hash": "df9078d2d3bcb6b364d4f054e84173c04efcdcc2d3143afd7bac99d750d223bf", "required_inputs": ["training_csv"], "output_contract": "vif,recommendation,n_complete"}]]

Receipt：2bc4e474c1864c9eb394d6a84ee4c940

## candidates：比较候选策略，哪一轮最好

选择：candidate_comparison

状态码：None

事实 / 计算结果：
- 比较 9 组候选策略，共同验证时间点已核对；第 1 轮得分最高，领先次优 7.289 分。
- 第 1 轮：得分 85.803，验证R²=0.9999，RMSE=0.3587，训练覆盖率=35.3%
- 第 5 轮：得分 78.514，验证R²=0.9996，RMSE=0.8762，训练覆盖率=9.8%
- 第 7 轮：得分 73.658，验证R²=0.9967，RMSE=2.5368，训练覆盖率=6.9%
- 第 4 轮：得分 73.432，验证R²=0.9964，RMSE=2.6325，训练覆盖率=6.4%
- 第 3 轮：得分 73.289，验证R²=0.9957，RMSE=2.8621，训练覆盖率=7.5%

推断：
- 按现有验证集评分规则，在本次比较范围内优先选择第 1 轮。

不确定项 / 所需输入：
- 比较重新计算现有候选指标的评分，没有重新训练候选，也没有用最终测试集选优。

数据证据：
- 05_optimization/optimization_report.json（JSON；SHA256 76241e26c04b）

选择依据：[[{"need": "候选策略", "matched_when_to_use": "比较候选策略和不同轮次结果，选择更好的策略", "similarity": 0.86357, "metadata_hash": "9d4d9fc5fa79e02883196bdea0d6fbe24d8068faec3c1b8a7ab99d509dc2df34", "required_inputs": ["optimization_json"], "output_contract": "ranking,best_round,score_margin"}, {"need": "哪一轮最好", "matched_when_to_use": "比较候选策略和不同轮次结果，选择更好的策略", "similarity": 0.29485, "metadata_hash": "9d4d9fc5fa79e02883196bdea0d6fbe24d8068faec3c1b8a7ab99d509dc2df34", "required_inputs": ["optimization_json"], "output_contract": "ranking,best_round,score_margin"}]]

Receipt：fc97db8b91904c23ad591d24cefce44d

## natural_language：看看煤气流量记录里有没有空白

选择：field_missing

状态码：None

事实 / 计算结果：
- gas_flow：标准化清洗前 4320 行，缺失 0 个（0.00%）；原始字段 gas_flow 的 4320 行中缺失 0 个

不确定项 / 所需输入：
- 原始/标准化空值与重采样空档是不同口径；此处不把清洗后的零空值当作原始完整。

数据证据：
- 02_standardization/standardized.csv（4320；SHA256 fa5385c50b0b）
- 01_input/source.csv（4320；SHA256 32e735072fbb）

选择依据：[[{"need": "记录里有没有空白", "matched_when_to_use": "寻找采集记录中的空白、断档和缺少的信息", "similarity": 0.57347, "metadata_hash": "49434e218f439a982d008ec2c6c59c1aa43fcf254a16e399ee159d20940ac3df", "required_inputs": ["standardized_csv", "source_csv"], "output_contract": "missing_count,missing_rate,absent_fields"}]]

Receipt：3e105dbf38f84f068cc918136ba1aa5a

## compound_semantic：综合看看煤气流量的数据问题以及模型误差

选择：anomaly_analysis、field_missing、model_error

状态码：None

事实 / 计算结果：
- gas_flow：规则标记异常 36/4320 个（0.83%）
- gas_flow：标准化清洗前 4320 行，缺失 0 个（0.00%）；原始字段 gas_flow 的 4320 行中缺失 0 个
- slab_discharge_temp：最终测试 646 个有效预测，R²=0.9999，RMSE=0.3663，MAE=0.2835，平均残差=-0.0275
- 较大误差位置 2026-08-01 19:00:00：实测 1203.7459，预测 1202.2776，残差 1.4684
- 较大误差位置 2026-08-01 19:03:40：实测 1194.6329，预测 1195.9925，残差 -1.3596
- 较大误差位置 2026-08-01 19:08:00：实测 1150.4458，预测 1151.6385，残差 -1.1927

推断：
- 上述分析来自同一任务；同时出现缺失、异常或模型误差不能单独证明它们之间的因果关系。

不确定项 / 所需输入：
- 异常为现有物理边界、阶跃、局部MAD规则命中，不等于已确认设备故障；未保存或替换修复后的数据。
- 阶跃阈值作用于相邻记录；记录间隔变化可能影响解释。
- 原始/标准化空值与重采样空档是不同口径；此处不把清洗后的零空值当作原始完整。
- 使用历史实测输出的单步预测误差，不能推断自由滚动预测或现场控制效果。
- 残差自相关按有效预测记录顺序计算，lag不是跨时间空档的物理秒数。

数据证据：
- 02_standardization/standardized.csv（4320；SHA256 fa5385c50b0b）
- 01_input/source.csv（4320；SHA256 32e735072fbb）
- 04_modeling/03_system_identification/final_test_predictions.csv（646；SHA256 ee0952a51890）

选择依据：[[{"need": "数据问题", "matched_when_to_use": "诊断数据质量问题，检查数值的有效性", "similarity": 0.59552, "metadata_hash": "9dc22881c7199a63ed9bc35827c2589e90d75282f74465c277f8fc9139e55981", "required_inputs": ["standardized_csv", "variable_spec"], "output_contract": "anomaly_count,anomaly_rate,examples"}], [{"need": "数据问题", "matched_when_to_use": "诊断数据质量问题，检查记录的完整性", "similarity": 0.57796, "metadata_hash": "49434e218f439a982d008ec2c6c59c1aa43fcf254a16e399ee159d20940ac3df", "required_inputs": ["standardized_csv", "source_csv"], "output_contract": "missing_count,missing_rate,absent_fields"}], [{"need": "模型误差", "matched_when_to_use": "评估模型预测误差、残差和拟合效果", "similarity": 0.62929, "metadata_hash": "1df3ff735cd78d468d7ef726ffce187c51a00ebb0ded75bab48956cb306329f8", "required_inputs": ["test_predictions_csv"], "output_contract": "metrics,bias,worst,residual_autocorrelation"}]]

Receipt：a8d13e9c875848e2a6662105ba31623c

## unavailable：帮我预测明天的钢价

选择：无可用分析能力

状态码：ANALYSIS_CAPABILITY_NOT_AVAILABLE

不确定项 / 所需输入：
- 基于Skill metadata与contract的语义匹配。
- ANALYSIS_CAPABILITY_NOT_AVAILABLE
- 当前未覆盖的分析能力：帮我预测明天钢价

选择依据：[]

Receipt：6ec9d104964c468680f8c2261f4e6b39

## missing_data：分析当前模型的预测误差

选择：model_error

状态码：None

不确定项 / 所需输入：
- 需要当前任务的数据产物：test_predictions_csv

选择依据：[[{"need": "模型预测误差", "matched_when_to_use": "评估模型预测误差、残差和拟合效果", "similarity": 0.94639, "metadata_hash": "1df3ff735cd78d468d7ef726ffce187c51a00ebb0ded75bab48956cb306329f8", "required_inputs": ["test_predictions_csv"], "output_contract": "metrics,bias,worst,residual_autocorrelation"}]]

Receipt：4a9e949cbe7e4c5eaafc8e28246aeef0
