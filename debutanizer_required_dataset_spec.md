# 脱丁烷塔补充数据要求

用途：现有物理量脱丁烷塔契约的通用 MD 主链验收。请同时提供原始 CSV、字段说明和来源说明；不要只提供无法还原的归一化矩阵。

| 标准字段 | 物理意义 / 角色 | Registry 单位 | 当前物理范围 |
|---|---|---|---|
| timestamp | 真实采集时间 / time | datetime | 单调、无重复，保留时区 |
| top_temperature | 塔顶温度 / input,state | degC | 20–120 |
| top_pressure | 塔顶压力 / input,state | Pa | 0–2,000,000 |
| reflux_flow | 回流流量 / input,manipulated | t/h | 0–500 |
| next_process_flow | 后续流程流量 / input,manipulated | t/h | 0–500 |
| tray6_temperature | 第六塔板温度 / input,state | degC | 20–150 |
| bottom_temperature_a | 塔底第一测温点 / input,state | degC | 50–180 |
| bottom_temperature_b | 塔底第二测温点 / input,state | degC | 50–180 |
| bottom_butane_content | 塔底 C4 含量 / target,controlled | percent | 0–10 |

所有字段必须存在；字段存在不等于每行都必须有值。允许保留真实缺测，不得填造 target。timestamp 不允许缺失；输入缺失保留并由既有因果清洗处理，长缺口可能导致 unavailable。目标必须在三个独立时间分区都有足够真实观测；不能用插值补齐独立测试真值。

建议采样周期：模板为 60 秒。必须记录实际周期，不能将纯样本序号伪装成真实秒数。现有入口最低 150 行是工程门槛，不是足够辨识的保证；建议至少 1,000 个连续采样点，覆盖多个真实运行变化与至少数倍已知滞后。保存实验室采样、分析时间、对齐方法和任何已做的目标平移。当前领域元数据的测量滞后为 30–75 分钟；不能未知时默认再平移一次。

上述范围来自当前模板，不用于反推缩放。若现场量纲/边界不同，先用现场元数据核实后做独立配置评审，而不是压缩数据以通过门禁。压力可明确标注 kPa，由既有单位转换处理；不要给无量纲 U2 默认贴 Pa 标签。

## 归一化数据必须附带

- source_file、完整 source_hash（SHA256）、数据所有者/采集来源、元数据证据文件及其版本。
- 每字段 source_column → standard_field，原始单位；timestamp 是否真实、时区和实际采样周期。
- 明确 normalization_method：当前离线工具支持 minmax_0_1 或 zscore。
- minmax_0_1：逐字段原始 min、max，公式 `x=z*(max-min)+min`。不能用当前 CSV 最小最大值或模板上下界替代训练时缩放参数。
- zscore：逐字段原始 mean、std，公式 `x=z*std+mean`；std 必须有限且大于零。
- 若有 clipping、log、Box-Cox、分段变换、丢失符号等，另附精确可逆步骤；仅 min/max 不足以恢复不可逆处理。
- 缩放器拟合的数据范围、是否涉及验证/测试数据、目标是否已平移及偏移单位。

`core/services/dataset_evidence.py::restore_normalized_fields` 是离线显式工具，不接入 Runtime 自动绕过门禁。它校验源文件 hash、字段/单位和数值参数，返回恢复副本与审计记录，不覆盖源文件。元数据真实性仍需核验，拥有一组格式合法参数不等于获得可信物理量。

提交后仍需自动场景识别、字段/单位门禁、冻结分区及完整 MD 链验证；不能仅凭 header 匹配判定 PASS。
