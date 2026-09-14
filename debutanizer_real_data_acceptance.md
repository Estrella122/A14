# 脱丁烷真实数据验收

真实来源找到了，符合当前契约的可执行数据没有找到。Pipeline UNAVAILABLE；Modeling NOT_EXECUTED；本轮run_id=null，12 Skill未执行。

[大学来源](https://home.isr.uc.pt/~rui/publications/datasets.html)说明来自真实塔；实际原包u1–u7/y是0–1值，缺可信逐字段inverse和物理时间。[新CSV镜像](https://github.com/StevenShaw98/Debutanizer-Column-Process)没有补足这些元数据。[工厂候选](https://github.com/LostRunes/debutanizer-model)有11399记录，但重沸器出口不能当第二底温、进料不能当下游流量，C4H6/C4H8不能直接当丁烷目标。

当前七输入为top_temperature、top_pressure、reflux_flow、next_process_flow、tray6_temperature、bottom_temperature_a/b，目标bottom_butane_content，timestamp必需。详情及物理语义元数据冻结于three_scene_real_runtime.json/contracts。安全门禁保持两个跨测点反例REVIEW_REQUIRED，不借模型高置信补缺。

未修改alias/required，未逆缩放、未填充或复制温度。没有可冻结真实模型，因此validation/test/persistence/AR-ARX/稳定性/10步/自由仿真/残差/白噪声/test leakage数值均为NOT_EXECUTED，不复用其他数据的指标。
