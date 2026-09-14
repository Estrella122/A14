# debutanizer_column 数据交付规范

按当前仓库 integrations/standardization/standards/scenarios/debutanizer_column/fields.csv 与 template.json 生成，不修改契约。

| required field | 单位 | 角色 | 物理说明 |
| --- | --- | --- | --- |
| timestamp | datetime | time | 炼油脱丁烷塔DCS或历史数据库采样时间 |
| top_temperature | degC | state | 脱丁烷精馏塔塔顶温度 |
| top_pressure | Pa | state | 脱丁烷精馏塔塔顶压力 |
| reflux_flow | t/h | manipulated | 塔顶回流流量或回流泵出口流量 |
| next_process_flow | t/h | manipulated | 脱丁烷塔流向下一流程的产品或侧线流量 |
| tray6_temperature | degC | state | 脱丁烷塔第六塔板温度或灵敏板温度 |
| bottom_temperature_a | degC | state | 脱丁烷塔塔底第一温度测点 |
| bottom_temperature_b | degC | state | 脱丁烷塔塔底第二温度测点 |
| bottom_butane_content | percent | controlled | 塔底物流中丁烷/C4组分浓度软测量目标；质量化验通常滞后30-75分钟 |

目标：bottom_butane_content。输入：top_temperature, top_pressure, reflux_flow, next_process_flow, tray6_temperature, bottom_temperature_a, bottom_temperature_b。optional：sample_index。

采样：模板处理默认 60 秒；请交付原生采样周期、时区、时间戳精度、数据缺口/停机/换批标识。实际周期必须与记录一致，模板默认值不能当源数据采样证明。允许可核验的真实起始时刻+原生采样索引，由独立转换脚本构造时间轴；不得编造日历时间。

最低规模：现有入口至少150行，对应规则采样下至少8940秒时间跨度；这是工程入口下限，不保证模型有效或全部阶段可执行。数据量还须覆盖冻结分区、guard、滞后和有效动态片段。建议提供多批次/多个稳态与过渡、数日连续原始数据；脱丁烷应覆盖30–75分钟化验滞后及多次工况变化。

缺失：每个required必须有真实测量记录；时间必须可解析、顺序明确；target不能全缺失，不得把补值当实测标签。请给逐字段missing/quality flags、连续缺口长度。现有清洗最多向前补6个输入采样点，target缺失保留；没有新增统一百分比阈值，是否足够由原有分区和数值门禁判断。

元数据：厂/实验编号、同一设备与时段证明、采集系统/校准记录、完整点表、位置/通道/流向、单位/基准状态、target测量方式/湿干基或浓度基准、化验采样与结果可用时间、原文件SHA256、可使用与再分发许可。

归一化：优先原始物理量。若只有缩放数据，需原公式（min-max/z-score或有文档自定义）、每字段参数、source_column身份、单位、源hash与变换/移位记录；缺任一项不能inverse。不得用上下限估计参数。

同一原文件来自同一过程/实验/时间上下文。不能拼接不同工厂列。rename/单位换算/时间解析需保留原文件，脚本输出source/output hash、renames、unit_conversions、time_operations、inverse_transform、dropped_columns、warnings；完整final gate与预检ELIGIBLE后才执行12 Skill。

特定禁止：重沸器出口替代第二塔底测点、进料替代下游流量、风机转速替代体积风量、车间湿度替代排气湿度、原料含水率替代产品含水率。
