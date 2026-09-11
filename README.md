# ProcessPilot A14

面向工业时序数据的场景识别、字段与单位标准化、因果清洗、动态段筛选、AR/ARX 系统辨识、离线寻优和工程评审系统。

当前正式保留三套比赛场景：钢铁高炉铁水质量预测、炼油脱丁烷精馏塔和工业干燥器。高炉场景提供带 CC BY 4.0 来源说明的 Mendeley 真实过程数据演示切片，并对非等间隔铁水化验采用只向后匹配的因果对齐；脱丁烷塔保留30–75分钟测量滞后和物理量字段规则；工业干燥器支持10秒采样、3输入3输出及共享输入的多输出ARX模型组。离线指标通过不代表已经具备生产投运条件。

## 环境

- Python 3.12+
- Node.js 20.19+ 或 22.12+

## 安装与运行

```bash
npm run setup
npm run dev
```

`npm run setup` 会在下载后的本地工程中创建 `.venv`、安装 Python 和前端依赖，并执行 Django 配置检查。浏览器入口为：

- Agent 中枢：<http://127.0.0.1:5176/agent-review/>
- 项目驾驶舱：<http://127.0.0.1:5176/overview/>
- 后端 API：<http://127.0.0.1:8000/api/>

## 验证

```bash
npm run test:backend
npm run build
```

高炉演示可直接上传 `frontend/public/datasets/blast_furnace_real_720h.csv`；工业干燥器可上传 `演示数据/工业干燥器_10秒_867条_3输入3输出_合成验收数据.csv`。后者是合成验收数据，不代表真实工厂数据。

脱丁烷塔数据的上游公开副本没有明确再分发许可证，因此仓库仅保留适配代码和来源说明，不重新发布数据文件。取得合法数据副本后，按 `datasets/public/debutanizer/README.md` 操作。

更完整的说明见 [使用说明.md](使用说明.md)，上线评审要求见 [docs/deployment_acceptance.md](docs/deployment_acceptance.md)。
