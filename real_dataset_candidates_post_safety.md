# 安全修复后的真实候选预检

沿用 30 个已登记来源的完整 GT/来源元数据，重新运行映射；不是重新下载并独立认证 30 份数据。完整 schema、来源、单位与已有原文件 SHA 见 real_field_ground_truth.json；当前接受 trace 见 datasets/field_acceptance_safety/after.json。

| scene | dataset | source type | GT coverage | contract | usable | reject reason |
| --- | --- | --- | --- | --- | --- | --- |
| blast_furnace | Fixed Mendeley derived 720h | DERIVED | 6/6 | CAN_RUN_NOW | yes | — |
| debutanizer_column | Fortuna 文本镜像 | BENCHMARK | 0/9 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| debutanizer_column | Coimbra 大学原始 MAT 包 | PUBLIC_REAL_PROCESS / BENCHMARK | 0/9 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| debutanizer_column | DC-dataset CSV 镜像 | BENCHMARK | 0/9 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| debutanizer_column | LostRunes DB DATA-B | REAL_PLANT (作者声明) | 2/9 | MIXED_LIMITATION | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| debutanizer_column | 本地 360 行 raw sample | BENCHMARK / 原始来源未证实 | 0/9 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| debutanizer_column | Danny-Taehyun-Kim hybrid demo | SYNTHETIC | 0/9 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| debutanizer_column | LPG composition paper | BENCHMARK / paper lead | 0/9 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| debutanizer_column | Column flooding paper | BENCHMARK / paper lead | 0/9 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| debutanizer_column | Fortuna 其他复用仓库 | BENCHMARK / paper lead | 0/9 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | DAISY 96-016 industrial dryer | PUBLIC_REAL_PROCESS | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | Coffee microwave/oven temperature experiment | PUBLIC_EXPERIMENT | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | Filter media drying moisture | PUBLIC_EXPERIMENT | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | Solar multipurpose dryer | PUBLIC_EXPERIMENT | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | Solar biomass fish dryer | PUBLIC_EXPERIMENT | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | Industrial laundry exhaust | DERIVED / REAL_PLANT | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | LARCO tumble dryers | PUBLIC_EXPERIMENT | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | WUR EHD dryer model | DERIVED | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | Rotary potash dryer paper | paper lead | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | Batch rotary NARX paper | paper lead | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | Rotary nickel CO paper | paper lead | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | 本地 867 行合成验收集 | SYNTHETIC | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | 本地 360 行 dryer raw sample | SYNTHETIC / 来源链待核实 | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| debutanizer_column | StevenShaw98 Fortuna CSV | BENCHMARK / real origin claimed | 0/9 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| debutanizer_column | Basque refinery pentanes classification | REAL_PLANT (paper lead) | 0/9 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| debutanizer_column | UTP CRU debutanizer thesis | REAL_PLANT (thesis lead) | 0/9 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | Tobacco Primary Processing data2 | REAL_PLANT (publisher description) | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | Solar dryer with thermal storage | PUBLIC_EXPERIMENT | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | Kiln beech-chip residence time | PUBLIC_EXPERIMENT | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |
| industrial_dryer | Cassava dryer IoT design files | PUBLIC_EXPERIMENT (design lead) | 0/7 | DATA_LIMITED | no | 缺物理变量/单位/采样/源文件，详见逐字段GT |

本次有限联网补充：

| scene | dataset | source | coverage | usable | 原因 |
| --- | --- | --- | --- | --- | --- |
| debutanizer | Ujjwal-1267 镜像 | research GitHub | 0/9 可核验物理契约 | no | 2394×8，U1…U7/y，文件声明 y 已移 8 样本；无可信单位/inverse/绝对时间证据 |
| dryer | HPD TF1 v3 | university Mendeley，CC BY 4.0 | 未提供可核验过程表 | no | 设备硬件资料，不能当连续测量数据 |
| dryer | HPD TF3+ v2 | university Mendeley，CC BY 4.0 | 未提供可核验过程表 | no | CAD/设备设计条目，不能证明 required 测点 |

[Ujjwal 源文件](https://github.com/Ujjwal-1267/industrial-debutanizer-soft-sensor/blob/main/data/debutanizer_data.txt)已下载到 runtime/data_validation/post_safety，原文头部明确时间移位；不二次移位、不推断采样秒数。授权再分发未核验，未推送原文件。

[HPD TF1](https://data.mendeley.com/datasets/g9w6ct4cgk/3)描述实验干燥器硬件；[HPD TF3+](https://data.mendeley.com/datasets/vg7c8dh365/2)归类为 CAD。页面没有提供本任务所需的同步过程列、rows、target、缺失/常数率、采样时间与 inverse metadata，因此这些指标为未知，不能填零，也不能当合格数据进入 Pipeline。

下载镜像的数值规模/缺失/常数统计记录在 datasets/field_acceptance_safety/new_candidate_preflight.json；范围仅作数据尺度记录，不作为身份或可逆性证明。没有跨实验拼接，也没有用 synthetic 替代。
