# 最终随机盲测包

- 随机种子：`20260727`
- `random_raw_timeseries.csv`：240 行随机污水曝气原始时序数据，可直接上传到 Agent。
- `random_field_challenge.csv`：272 条相关字段与 60 条无关字段的带标签盲测集。
- `random_challenge_report.json`：验收门槛、字段指标、整文件指标和错误案例。

本轮结果：字段 Top-1 99.26%，相关字段接收召回 99.26%，无关字段误接收 0%；整文件 13 个工艺字段全部正确映射，必需字段覆盖率 100%，文件状态为 `ready`。

复现命令：

```bash
PYTHONPATH=. python3 training/random_challenge.py --seed 20260727 --variants 4 --output training_data/random_challenge_final
```
