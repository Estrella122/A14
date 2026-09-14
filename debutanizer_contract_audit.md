# 脱丁烷塔完整契约审计

七个输入均来自现有 field_roles.inputs，不属于仅展示字段。core/skills/context.py::build_scene_context 读取角色，stage_adapters.py::_agent 将输入及目标加入清洗spec；core_executors.py 消费input_columns进行分析。通用算法理论可运行不同输入集，不等于本场景测点可以删减。当前不满足用户要求的四项降级条件，required保持不变。

A：timestamp、七输入、目标均保留必需。B：sample_index 为可选辅助字段。C：已有明确同义别名见表；匿名归一化列命中别名不能证明物理值有效。

|字段|角色|单位|必需|范围|别名|
|---|---|---|---|---|---|
| timestamp | time | datetime | true | .. | 采集时间 / 记录时间 / 时间 / sample_timestamp / sequence_time / timestamp / time / TIME / DATETIME / TS |
| top_temperature | state | degC | true | 20..120 | U1 / u1 / Top_Temperature / top temperature / 塔顶温度 / 顶温 / DEBUT_TOP_TEMP / TT_TOP |
| top_pressure | state | Pa | true | 0..2000000 | U2 / u2 / Top_Pressure / top pressure / 塔顶压力 / 塔压 / DEBUT_TOP_PRESS / PT_TOP |
| reflux_flow | manipulated | t/h | true | 0..500 | U3 / u3 / Reflux_Flow / reflux flow / 回流量 / 回流流量 / DEBUT_REFLUX / FT_REFLUX |
| next_process_flow | manipulated | t/h | true | 0..500 | U4 / u4 / Flow_To_Next_Process / flow to next process / 后续流程流量 / 塔底产品流量 / 出料流量 / DEBUT_PRODUCT_FLOW / FT_PRODUCT |
| tray6_temperature | state | degC | true | 20..150 | U5 / u5 / Tray6_Temperature / sixth tray temperature / 第六塔板温度 / 灵敏板温度 / DEBUT_TRAY6_TEMP / TT_TRAY6 |
| bottom_temperature_a | state | degC | true | 50..180 | U6 / u6 / Bottom_Temperature_A / bottom temperature a / 塔底温度A / 塔釜温度A / DEBUT_BOTTOM_TEMP_A / TT_BOTTOM_A / bottom_temp_a |
| bottom_temperature_b | state | degC | true | 50..180 | U7 / u7 / Bottom_Temperature_B / bottom temperature b / 塔底温度B / 塔釜温度B / DEBUT_BOTTOM_TEMP_B / TT_BOTTOM_B / bottom_temp_b |
| bottom_butane_content | controlled | percent | true | 0..10 | U8 / u8 / y / Butane_Content / butane content / C4浓度 / 塔底C4 / 塔底丁烷含量 / 丁烷含量 / BOTTOM_C4 / C4_CONTENT / LIMS_C4 |
| sample_index | identifier | string | false | 0.. | sample / row_number / sample_index / 序号 |

## SceneContext 与约束
```json
{
  "scenario_id": "debutanizer_column",
  "scenario_name": "炼油脱丁烷塔",
  "dataset_ref": "/Users/komi/Documents/ChatGPT/作品修复/A14/integrations/standardization/training_data/raw_samples/debutanizer_column_raw.csv",
  "timestamp_column": "timestamp",
  "input_columns": [
    "top_temperature",
    "top_pressure",
    "reflux_flow",
    "next_process_flow",
    "tray6_temperature",
    "bottom_temperature_a",
    "bottom_temperature_b"
  ],
  "target_column": "bottom_butane_content",
  "units": {
    "timestamp": "datetime",
    "top_temperature": "degC",
    "top_pressure": "Pa",
    "reflux_flow": "t/h",
    "next_process_flow": "t/h",
    "tray6_temperature": "degC",
    "bottom_temperature_a": "degC",
    "bottom_temperature_b": "degC",
    "bottom_butane_content": "percent",
    "sample_index": "string"
  },
  "sampling_interval": 60,
  "constraints": {
    "physical_bounds_source": "fields.csv",
    "missing_target_policy": "preserve_nan",
    "train_validation_test": "chronological_60_20_20_v2",
    "strict_segment_score": 80,
    "snr_threshold_db": 10,
    "minimum_rows": 150,
    "causal_alignment": "past_only",
    "lab_tolerance_hours": null
  },
  "default_parameters": {
    "resample_seconds": 60,
    "max_lag": 75,
    "window_length": 30,
    "step": 15,
    "top_k": 5
  },
  "metadata": {
    "family": "石油炼制",
    "display": {
      "name": "炼油脱丁烷塔",
      "industry": "石油炼制",
      "process_unit": "脱丁烷精馏塔软测量"
    },
    "model_outputs": [
      "bottom_butane_content"
    ],
    "source": null,
    "skill_overrides": {},
    "config_source": "ScenarioRepository",
    "project_context_scene": null
  }
}
```

配置60秒是默认值，不是公开基准实际采样间隔的证据；不得为无时间数据制造真实日历时间。模板说明中“U1-U8可接入”仅代表表头别名，不能越过归一化/物理单位门禁。当前说明偏宽泛，本轮不改变算法行为。

old_contract = new_contract。affected_skills：清洗、SNR、动态段、时滞、共线性、ARX等使用这些输入；没有仅展示的温度字段。regression_tests：core/test_debutanizer_contract.py。

专项反例实测发现 trained_model_auto 可跨测点错误匹配，详见 acceptance 报告。明确alias白名单没有这些同义关系；数据接入必须保留人工来源核验。测试结果5通过/1失败/1跳过。
