# 公开脱丁烷塔工业数据

该数据来自 Fortuna 等人的工业脱丁烷塔软测量基准，共2394个连续样本。7个输入依次为塔顶温度、塔顶压力、回流流量、流向下一流程的流量、第六塔板温度、塔底温度A和塔底温度B；输出为塔底丁烷含量。

原始文件：`debutanizer_data.txt`。项目输入：`debutanizer_processpilot.csv`。

公开副本没有给出真实日历时间、采样周期或反归一化参数。`sample_timestamp` 是为保存样本顺序生成的派生时间轴。因此所有时滞只能报告为采样点数，数值只能解释为归一化量。源文件说明输出已经平移8个样本以补偿实验室测量时滞，建模报告必须保留这一事实。

来源：https://github.com/Ujjwal-1267/industrial-debutanizer-soft-sensor

参考论文 DOI：https://doi.org/10.1016/j.conengprac.2004.04.013

变量定义交叉核对：https://www.mdpi.com/1424-8220/22/18/6887

当前下载仓库未提供明确的数据再分发许可证。该副本仅用于本地研究与工程验收；对外分享或商业使用前，应向原数据提供方确认授权。公开可访问不等于允许重新分发。

运行：

```bash
.venv/bin/python datasets/public/debutanizer/prepare_dataset.py
```
