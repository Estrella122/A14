# 真实中控验收闭环

本目录用于验收 Skill 路由和系统辨识。合成训练集不能替代这里的人工标注数据。

## 1. 标注真实问句

复制 `real_routing_gold.template.jsonl` 为 `real_routing_gold.jsonl`。每行一个 JSON 对象：

- `text`：脱敏后的中控原话。
- `labels`：用户直接要求的业务 Skill ID；无匹配技能时为空数组。
- `mode`：`analyze` 或 `execute`。
- `stop_after`：`evidence_only`、`standardization`、`cleaning`、`selection`、`modeling` 或 `report`。
- `critical_no_execute`：否定、假设、引用、询问等绝不能启动算法的请求设为 `true`。
- `split`：同一会话或同一意图模板必须放在同一分区；最终验收使用 `test`。
- `review_status`：只有两名复核人达成一致后改成 `approved`。

标注完成后运行：

```bash
.venv/bin/python acceptance/evaluate_real_routing.py acceptance/real_routing_gold.jsonl
```

脚本会生成 `acceptance/reports/real_routing_acceptance.json`。门禁要求：测试集不少于30条、Skill集合准确率≥95%、阶段准确率≥98%、严重误执行为0、未知请求拒绝率≥95%。样本不足会明确给出 `insufficient_evidence`，不会输出虚假的生产准确率。

## 2. 验收系统辨识证据

```bash
.venv/bin/python acceptance/evaluate_model_evidence.py
```

脚本读取最新流水线快照并生成 `acceptance/reports/model_evidence_acceptance.json`。只有外部输入模型、独立测试优于持续值基线、10步预测有效、自由仿真有效、残差与稳定性诊断齐全，才允许标记为候选通过。

## 3. 数据收集要求

新一批加热炉数据至少应覆盖明确的燃气或空气调节动作、动作前后稳定段、设定值、阀位、流量、各炉区温度、出钢温度、运行模式以及人工操作记录。采集期间不要为追求模型分数绕过联锁或生产操作规程。

可直接按 `furnace_data_collection.template.csv` 的字段组织数据；已有字段名不同也可以保留，但需提供单位和含义。
