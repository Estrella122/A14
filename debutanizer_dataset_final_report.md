# 脱丁烷塔数据最终报告

结论：Pipeline UNAVAILABLE；Modeling PARTIAL（未执行，不表示模型失败）。

[Coimbra 大学原始包](https://home.isr.uc.pt/~fasouza/debutanizer_fortuna_dataset.zip)已实际下载并解析：仅 debutanizer.mat，u1–u7、y 各2394条、范围均0–1，没有时间、单位或 inverse scaling 参数。文本镜像与本地公开数据 metadata 的 SHA256一致；不代表360行样本与其同源。未做逆变换。

[LostRunes 物理过程候选](https://github.com/LostRunes/debutanizer-model)实际CSV有11399条数据（11401条解析记录减去点号/单位两行），不是按README的11343条直接记账。数据含列顶、列底、重沸器出口、控制塔板、回流、进料、蒸汽及两种C4组分。缺第二底温、明确第六塔板、下游流量和可确认的丁烷目标。不能把测点不同当alias；编码中的压力/温度单位需源方确认。

当前需要：真实 timestamp、top_temperature、top_pressure、reflux_flow、next_process_flow、tray6_temperature、bottom_temperature_a/b、bottom_butane_content。流量质量/体积基准、压力表压/绝压及目标组分必须明确。当前配置不改。更多论文及镜像的下载/许可/门禁见候选总表。

所有新候选未通过前置门禁，因此本轮未启动脱丁烷塔12节点数值执行，没有制造“成功”运行ID。获得完整物理数据或来源可验证的逐字段缩放元数据后，才能使用既有纯MD链。
