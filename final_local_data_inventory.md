# 最终本地盘点

rg --files --hidden --no-ignore 覆盖 datasets、datasets/real_validation、training、演示数据、runtime、runtime/data_validation、reports、docs、integrations、SOURCE 与下载/转换 manifest；排除 .git、venv、node_modules。命中 3775 条路径，包含历史衍生产物，不是同等数量独立真实数据。

当前可取得的12个源文件逐一重新计算hash，全部与既有库存相符。31个来源记录沿用已有来源证据，只有原文件实际存在的条目带 hash_revalidated=true。未重下 Fortuna/LostRunes/DAISY/烟草文件。

| dataset | type | file status | hash revalidated | local file |
| --- | --- | --- | --- | --- |
| Fixed Mendeley derived 720h | DERIVED_REAL | ACQUIRED_FILE | True | /Users/komi/Documents/ChatGPT/作品修复/A14/frontend/public/datasets/blast_furnace_real_720h.csv |
| Fortuna 文本镜像 | BENCHMARK_REAL | ACQUIRED_FILE | True | /Users/komi/Documents/ChatGPT/作品修复/A14/runtime/data_validation/public_candidates/fortuna.txt |
| Coimbra 大学原始 MAT 包 | BENCHMARK_REAL | ACQUIRED_FILE | True | /Users/komi/Documents/ChatGPT/作品修复/A14/runtime/data_validation/public_candidates/fasouza_fortuna.zip |
| DC-dataset CSV 镜像 | BENCHMARK_REAL | ACQUIRED_FILE | True | /Users/komi/Documents/ChatGPT/作品修复/A14/runtime/data_validation/public_candidates/dc.csv |
| LostRunes DB DATA-B | UNKNOWN | ACQUIRED_FILE | True | /Users/komi/Documents/ChatGPT/作品修复/A14/runtime/data_validation/public_candidates/lost_plant.csv |
| 本地 360 行 raw sample | UNKNOWN | ACQUIRED_FILE | True | /Users/komi/Documents/ChatGPT/作品修复/A14/integrations/standardization/training_data/raw_samples/debutanizer_column_raw.csv |
| Danny-Taehyun-Kim hybrid demo | SYNTHETIC | SOURCE_REFERENCE_ONLY | False | None |
| LPG composition paper | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| Column flooding paper | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| Fortuna 其他复用仓库 | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| DAISY 96-016 industrial dryer | PUBLIC_REAL_PROCESS | ACQUIRED_FILE | True | /Users/komi/Documents/ChatGPT/作品修复/A14/runtime/data_validation/public_candidates/daisy_dryer.gz |
| Coffee microwave/oven temperature experiment | PUBLIC_EXPERIMENT | ACQUIRED_FILE | True | /Users/komi/Documents/ChatGPT/作品修复/A14/runtime/data_validation/public_candidates/coffee.xlsx |
| Filter media drying moisture | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| Solar multipurpose dryer | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| Solar biomass fish dryer | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| Industrial laundry exhaust | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| LARCO tumble dryers | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| WUR EHD dryer model | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| Rotary potash dryer paper | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| Batch rotary NARX paper | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| Rotary nickel CO paper | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| 本地 867 行合成验收集 | SYNTHETIC | ACQUIRED_FILE | True | /Users/komi/Documents/ChatGPT/作品修复/A14/演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv |
| 本地 360 行 dryer raw sample | SYNTHETIC | ACQUIRED_FILE | True | /Users/komi/Documents/ChatGPT/作品修复/A14/integrations/standardization/training_data/raw_samples/industrial_dryer_raw.csv |
| StevenShaw98 Fortuna CSV | BENCHMARK_REAL | ACQUIRED_FILE | True | /Users/komi/Documents/ChatGPT/作品修复/A14/runtime/data_validation/real_search/stevenshaw_debutanizer.csv |
| Basque refinery pentanes classification | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| UTP CRU debutanizer thesis | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| Tobacco Primary Processing data2 | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| Solar dryer with thermal storage | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| Kiln beech-chip residence time | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| Cassava dryer IoT design files | UNKNOWN | SOURCE_REFERENCE_ONLY | False | None |
| KLD-2 tobacco processed subset / transformer-lstm | DERIVED_REAL | ACQUIRED_FILE | True | runtime/data_validation/final_search/tobacco.xlsx |

全路径：datasets/real_validation/closeout/local_files.txt；完整来源档案：closeout/candidates.json。重用原始DAISY说明、烟草字段复核与逐字段gate结果；没有把runtime中多次生成的同源CSV计为新数据。
