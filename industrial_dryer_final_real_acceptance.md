# 工业干燥器最终真实验收

未找到满足全部 required 的真实数据。Pipeline=UNAVAILABLE；12 个数值 Executor 未启动；Modeling=NOT_EXECUTED。

DAISY 本轮重新读原始说明：867 点、10 秒采样；输入是燃料流量、排气风机转速、原料流量；输出是干球/湿球温度、原料含水率。源未标物理单位/偏置。风机转速不能当 Nm3/h；原料含水率不能当产品含水率；湿球温度不能当排气相对湿度。物理 GT coverage=0/7，属于 DATA_LIMITED/MISSING_METADATA，不是 Agent 训练问题。

新增实际文件 FL2409JJ9070-049.xlsx（Zenodo处理子集）800行9列。_time 为2024-09-26 00:45:19起的逐秒时间；出口含水率列 ZX_BBHS_OUTMATMOISTURE_PV。时间与出口水分有可解释来源依据，至多2/7物理候选，但这些不等于自动接受；当前 raw 自动0/7。其余列为入口含水率、累计物料、干燥实际/设定值、车间温湿度及 avg。累计物料≠湿进料流量，车间湿度≠排气湿度；板温/干燥设定也不能直接当热风温度，avg 未建立完整物理定义。

缺当前风量、湿进料流量、产品温度、排气湿度等证据；完整处理/缩放记录也不足。没有改字段 Agent 去接受它。原文件与逐字段人工复核记录：datasets/real_validation/tobacco_field_review.json；完整门禁结果：prechecks/tobacco_zenodo.json。

原论文描述完整原始工厂数据不公开，归档只含处理子集。许可详见 real_data_source_and_license_report.md。满足整套契约所需数据见 industrial_dryer_real_dataset_requirement.md。

本轮收尾复核：复用原文件并重新校验哈希/运行预检；结论未改变。最终收据见 three_scene_final_real_runtime.json；该场景 executions=[]，不把旧产物或规划节点当本次数值执行。
