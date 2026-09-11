# ProcessPilot A14

面向工业时序数据的场景识别、字段与单位标准化、因果清洗、动态段筛选、AR/ARX 系统辨识、离线寻优和工程评审系统。

当前内置钢厂加热炉、火电燃煤锅炉、污水曝气池、水泥回转窑、蒸馏塔和炼油脱丁烷塔六套字段规范。评审结果分为离线候选模型、软测量候选和闭环控制候选；离线指标通过不代表已经具备生产投运条件。

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

可以上传 `演示数据/A14_2号任务_合格测试数据_钢厂加热炉.csv` 完成全流程测试。该文件是合成演示数据，不代表真实工厂数据。

脱丁烷塔数据的上游公开副本没有明确再分发许可证，因此仓库仅保留适配代码和来源说明，不重新发布数据文件。取得合法数据副本后，按 `datasets/public/debutanizer/README.md` 操作。

更完整的说明见 [使用说明.md](使用说明.md)，上线评审要求见 [docs/deployment_acceptance.md](docs/deployment_acceptance.md)。
