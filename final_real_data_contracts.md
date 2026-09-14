# 最终真实物理契约

直接读取本轮仓库 fields.csv/template.json；哈希冻结在 datasets/real_validation/closeout/contracts.json。没有修改任何契约。

## debutanizer_column

| field | required | unit | role | description | accepted aliases |
| --- | --- | --- | --- | --- | --- |
| timestamp | true | datetime | time | 炼油脱丁烷塔DCS或历史数据库采样时间 | 采集时间/记录时间/时间/sample_timestamp/sequence_time/timestamp/time/TIME/DATETIME/TS |
| top_temperature | true | degC | state | 脱丁烷精馏塔塔顶温度 | U1/u1/Top_Temperature/top temperature/塔顶温度/顶温/DEBUT_TOP_TEMP/TT_TOP |
| top_pressure | true | Pa | state | 脱丁烷精馏塔塔顶压力 | U2/u2/Top_Pressure/top pressure/塔顶压力/塔压/DEBUT_TOP_PRESS/PT_TOP |
| reflux_flow | true | t/h | manipulated | 塔顶回流流量或回流泵出口流量 | U3/u3/Reflux_Flow/reflux flow/回流量/回流流量/DEBUT_REFLUX/FT_REFLUX |
| next_process_flow | true | t/h | manipulated | 脱丁烷塔流向下一流程的产品或侧线流量 | U4/u4/Flow_To_Next_Process/flow to next process/后续流程流量/塔底产品流量/出料流量/DEBUT_PRODUCT_FLOW/FT_PRODUCT |
| tray6_temperature | true | degC | state | 脱丁烷塔第六塔板温度或灵敏板温度 | U5/u5/Tray6_Temperature/sixth tray temperature/第六塔板温度/灵敏板温度/DEBUT_TRAY6_TEMP/TT_TRAY6 |
| bottom_temperature_a | true | degC | state | 脱丁烷塔塔底第一温度测点 | U6/u6/Bottom_Temperature_A/bottom temperature a/塔底温度A/塔釜温度A/DEBUT_BOTTOM_TEMP_A/TT_BOTTOM_A/bottom_temp_a |
| bottom_temperature_b | true | degC | state | 脱丁烷塔塔底第二温度测点 | U7/u7/Bottom_Temperature_B/bottom temperature b/塔底温度B/塔釜温度B/DEBUT_BOTTOM_TEMP_B/TT_BOTTOM_B/bottom_temp_b |
| bottom_butane_content | true | percent | controlled | 塔底物流中丁烷/C4组分浓度软测量目标；质量化验通常滞后30-75分钟 | U8/u8/y/Butane_Content/butane content/C4浓度/塔底C4/塔底丁烷含量/丁烷含量/BOTTOM_C4/C4_CONTENT/LIMS_C4 |
| sample_index | false | string | identifier | 样本顺序编号或历史数据行号 | sample/row_number/sample_index/序号 |

当前模板（包含 target、inputs、physical_semantics、sampling、constraints/defaults）：

```json

{
  "scenario_id": "debutanizer_column",
  "scenario_name": "炼油脱丁烷塔",
  "industry": "石油炼制",
  "process_unit": "脱丁烷精馏塔软测量",
  "version": "1.1.0",
  "dictionary": "fields.csv",
  "keywords": [
    "炼油",
    "脱丁烷塔",
    "精馏塔",
    "丁烷",
    "C4",
    "debutanizer",
    "butane",
    "refinery"
  ],
  "sampling_seconds": 60,
  "time_axis_type": "wall_clock",
  "timestamp_field": "timestamp",
  "primary_output": "bottom_butane_content",
  "measurement_delay_minutes": {
    "min": 30,
    "max": 75
  },
  "expected_rows": 2394,
  "notes": "炼油脱丁烷精馏塔软测量场景：7个温度/压力/流量输入预测塔底C4浓度，质量化验或软测量目标通常存在30-75分钟测量滞后。公开Fortuna样本仍可通过U1-U8别名接入，但若源数据为归一化值需保留数据来源说明。",
  "family": "石油炼制",
  "field_roles": {
    "timestamp": "timestamp",
    "inputs": [
      "top_temperature",
      "top_pressure",
      "reflux_flow",
      "next_process_flow",
      "tray6_temperature",
      "bottom_temperature_a",
      "bottom_temperature_b"
    ],
    "target": "bottom_butane_content",
    "optional_context": [
      "sample_index"
    ]
  },
  "units": {
    "source": "fields.csv",
    "column": "unit"
  },
  "aliases": {
    "source": "fields.csv",
    "column": "aliases"
  },
  "default_parameters": {
    "resample_seconds": 60,
    "max_lag": 75,
    "window_length": 30,
    "step": 15,
    "top_k": 5
  },
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
  "display": {
    "name": "炼油脱丁烷塔",
    "industry": "石油炼制",
    "process_unit": "脱丁烷精馏塔软测量"
  },
  "physical_semantics": {
    "top_temperature": {
      "canonical_name": "top_temperature",
      "quantity_type": "temperature",
      "physical_role": "process_measurement",
      "equipment_role": "column",
      "measurement_location": "column_top",
      "flow_direction": null,
      "unit_source": "fields.csv",
      "aliases_source": "fields.csv",
      "forbidden_relations": [
        "different_measurement_location",
        "different_equipment_role",
        "different_flow_direction"
      ]
    },
    "top_pressure": {
      "canonical_name": "top_pressure",
      "quantity_type": "pressure",
      "physical_role": "process_measurement",
      "equipment_role": "column",
      "measurement_location": "column_top",
      "flow_direction": null,
      "unit_source": "fields.csv",
      "aliases_source": "fields.csv",
      "forbidden_relations": [
        "different_measurement_location",
        "different_equipment_role",
        "different_flow_direction"
      ]
    },
    "reflux_flow": {
      "canonical_name": "reflux_flow",
      "quantity_type": "flow",
      "physical_role": "process_measurement",
      "equipment_role": "column",
      "measurement_location": "reflux_line",
      "flow_direction": "reflux",
      "unit_source": "fields.csv",
      "aliases_source": "fields.csv",
      "forbidden_relations": [
        "different_measurement_location",
        "different_equipment_role",
        "different_flow_direction"
      ]
    },
    "next_process_flow": {
      "canonical_name": "next_process_flow",
      "quantity_type": "flow",
      "physical_role": "process_measurement",
      "equipment_role": "column",
      "measurement_location": "downstream_line",
      "flow_direction": "downstream",
      "unit_source": "fields.csv",
      "aliases_source": "fields.csv",
      "forbidden_relations": [
        "different_measurement_location",
        "different_equipment_role",
        "different_flow_direction"
      ]
    },
    "tray6_temperature": {
      "canonical_name": "tray6_temperature",
      "quantity_type": "temperature",
      "physical_role": "process_measurement",
      "equipment_role": "column",
      "measurement_location": "tray_6",
      "flow_direction": null,
      "unit_source": "fields.csv",
      "aliases_source": "fields.csv",
      "forbidden_relations": [
        "different_measurement_location",
        "different_equipment_role",
        "different_flow_direction"
      ]
    },
    "bottom_temperature_a": {
      "canonical_name": "bottom_temperature_a",
      "quantity_type": "temperature",
      "physical_role": "process_measurement",
      "equipment_role": "column",
      "measurement_location": "column_bottom",
      "flow_direction": null,
      "unit_source": "fields.csv",
      "aliases_source": "fields.csv",
      "forbidden_relations": [
        "different_measurement_location",
        "different_equipment_role",
        "different_flow_direction"
      ],
      "measurement_channel": "a"
    },
    "bottom_temperature_b": {
      "canonical_name": "bottom_temperature_b",
      "quantity_type": "temperature",
      "physical_role": "process_measurement",
      "equipment_role": "column",
      "measurement_location": "column_bottom",
      "flow_direction": null,
      "unit_source": "fields.csv",
      "aliases_source": "fields.csv",
      "forbidden_relations": [
        "different_measurement_location",
        "different_equipment_role",
        "different_flow_direction"
      ],
      "measurement_channel": "b"
    },
    "bottom_butane_content": {
      "canonical_name": "bottom_butane_content",
      "quantity_type": "concentration",
      "physical_role": "process_measurement",
      "equipment_role": "column",
      "measurement_location": "column_bottom",
      "flow_direction": null,
      "unit_source": "fields.csv",
      "aliases_source": "fields.csv",
      "forbidden_relations": [
        "different_measurement_location",
        "different_equipment_role",
        "different_flow_direction"
      ]
    }
  }
}

```

## industrial_dryer

| field | required | unit | role | description | accepted aliases |
| --- | --- | --- | --- | --- | --- |
| timestamp | true | datetime | time | 工业时序采样时间 | 时间/采集时间/记录时间/TIME/DATETIME/TS |
| hot_air_temperature | true | degC | manipulated | 进入干燥器的热风温度 | 入口热风温度/进风温度/HOT_AIR_TEMP/INLET_AIR_TEMP |
| drying_air_flow | true | Nm3/h | manipulated | 进入干燥器的热风体积流量 | 热风流量/进风量/干燥空气流量/DRYING_AIR_FLOW/AIR_FLOW |
| wet_feed_rate | true | t/h | manipulated | 进入干燥器的湿物料质量流量 | 湿料流量/进料量/给料量/WET_FEED_RATE/FEED_RATE |
| product_moisture | true | percent | controlled | 干燥产品出口含水质量百分数 | 出口含水率/产品水分/物料含水率/PRODUCT_MOISTURE/OUTLET_MOISTURE |
| product_temperature | true | degC | controlled | 干燥产品离开设备时的温度 | 物料出口温度/产品温度/PRODUCT_TEMP/OUTLET_PRODUCT_TEMP |
| exhaust_humidity | true | percent | controlled | 干燥器尾气相对湿度 | 尾气湿度/出口空气湿度/排气湿度/EXHAUST_HUMIDITY/OUTLET_AIR_HUMIDITY |

当前模板（包含 target、inputs、physical_semantics、sampling、constraints/defaults）：

```json

{
  "scenario_id": "industrial_dryer",
  "scenario_name": "工业干燥器",
  "industry": "流程工业",
  "process_unit": "连续式热风工业干燥装置",
  "version": "1.0.0",
  "dictionary": "fields.csv",
  "keywords": [
    "工业干燥器",
    "干燥机",
    "烘干机",
    "热风干燥",
    "dryer",
    "drying unit"
  ],
  "sampling_seconds": 10,
  "timestamp_field": "timestamp",
  "primary_output": "product_moisture",
  "model_outputs": [
    "product_moisture",
    "product_temperature",
    "exhaust_humidity"
  ],
  "selection_window_samples": 18,
  "selection_step_samples": 6,
  "recognition": {
    "priority": 60,
    "min_evidence": 3,
    "min_confidence": 0.52,
    "conflicting_features": [
      "slab_discharge_temp",
      "bottom_butane_content",
      "dissolved_oxygen"
    ]
  },
  "data_provenance_required": [
    "source_system",
    "equipment_id",
    "collection_period",
    "instrument_traceability",
    "usage_authorization"
  ],
  "notes": "面向3输入3输出连续干燥装置；快速动态窗口为180秒、步长60秒，采用共享输入的多输出ARX模型组。",
  "family": "流程工业",
  "field_roles": {
    "timestamp": "timestamp",
    "inputs": [
      "hot_air_temperature",
      "drying_air_flow",
      "wet_feed_rate"
    ],
    "target": "product_moisture",
    "optional_context": []
  },
  "units": {
    "source": "fields.csv",
    "column": "unit"
  },
  "aliases": {
    "source": "fields.csv",
    "column": "aliases"
  },
  "default_parameters": {
    "resample_seconds": 10,
    "max_lag": 60,
    "window_length": 18,
    "step": 6,
    "top_k": 5
  },
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
  "display": {
    "name": "工业干燥器",
    "industry": "流程工业",
    "process_unit": "连续式热风工业干燥装置"
  }
}

```

## 已接受的来源元数据

final gate 的 field-scoped metadata：standard_field、scenario_id、evidence_source、unit；匿名/归一化列还需要 normalized=false 或 inverse_metadata+transform_applied。离线 inverse helper 额外检查 source_file、source_hash、normalization_method、inverse_transform_parameters。这些必须来自可靠原文件/文档，不是自行填写即真实。点位还需 scene/standard_field/source/unit 对应。

required 字段只有全部通过门禁且证据可信才 Contract PASS。Registry 单位默认和采样默认不是源设备的实测证明；缺少证据仍停留 review。
