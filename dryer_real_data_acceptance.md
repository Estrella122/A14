# 工业干燥器真实数据验收

可信实测来源已找到，但当前契约未通过。真实数据数值链本轮未执行；总体Pipeline PARTIAL（仅历史合成开发证据），真实Modeling NOT_EXECUTED。

[DAISY](https://homes.esat.kuleuven.be/~tokka/daisydata.html)有大学贡献者及867条10秒工业数据。但燃料流量/风机转速/原料水分与当前热风入口温度/Nm3每小时风量/产品水分不同；干湿球温度不能直接冒充排气湿度。绝对单位与偏置也缺失。

[烟草新线索](https://data.mendeley.com/datasets/v3bvdmccmm/1)具有真实生产描述，但原文件403，未验证连续湿料进料率、标准体积风量和排气相对湿度。[太阳能实验](https://data.mendeley.com/datasets/cgjpm86mwg/1)是批次称重，不能制造连续进料率。[咖啡实验](https://zenodo.org/records/16729583)已核验温度序列，但缺连续产品水分。

当前必需timestamp、hot_air_temperature、drying_air_flow、wet_feed_rate、product_moisture、product_temperature、exhaust_humidity。不把水分/湿度或原料/产品互换。867条synthetic不作为最终真实工业证明；本轮没有重新生成或运行它。

真实数据未执行，因此validation/test RMSE、baseline、relative improvement、AR vs ARX、稳定性、多步/仿真及残差均NOT_EXECUTED。历史合成指标留在dryer_dataset_final_report.md，不冒称真实模型结果。
