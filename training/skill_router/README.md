# Agent Skill 路由训练与复现

本目录训练的是 **Agent 选择哪一个业务 skill 的轻量路由分类器**，不是加热炉 ARX 模型，也不是对外部大语言模型做微调。现有 30 个 skill ID 保持不变：24 个业务技能参与分类，6 个编排技能由运行时按需添加。

## 已交付

- `data/train.jsonl`：400 个独立种子句扩写为 1,200 行；扩写仅限训练集。
- `data/validation.jsonl`：75 条独立表述，用于正则强度、拒绝阈值选择。
- `data/test.jsonl`：100 条留出样本，不参与拟合和调参。
- `../../core/skills/models/skill_router.json.gz`：已经训练好的模型，默认自动加载。
- `train.py`：训练、选择参数、导出 JSON 模型，核对导出推理与 sklearn 的数值一致性。
- `evaluate.py`：原始调度器与新调度器在同一份留出集上的对照验收。
- `baseline_runtime.py`：从原 ZIP 保留的调度实现，仅供评估。
- `reports/acceptance.json` / `reports/test_predictions.jsonl`：完整指标、逐例结果及失败例。
- `../../core/test_skill_routing.py`：否定、复合任务、上下文、依赖冲突和执行范围回归。

数据均由本次工作编写，来源标记为 `assistant_authored_synthetic`。它们不是现场日志，也未经过独立人工标注。因此本次分数只描述这份小规模合成测试；不代表真实业务准确率。

## 使用现成模型

按工程原有方式安装后端依赖并启动即可。推理只使用 Python 标准库，**不需要安装 scikit-learn，不需要外部模型 API、不需要额外启动模型服务**。交付包不含虚拟环境或本机依赖。

在工程根目录用 Python 3.12+：

```bash
python -m pip install -r requirements.txt
python training/skill_router/predict.py "不要训练模型，只导出已有报告"
python manage.py runserver 127.0.0.1:8000
```

若沿用原工程的 `npm run setup`，它会按原有流程创建本地 `.venv`；之后可用该环境的 Python 运行以上命令。无需虚拟环境时直接使用已有的 Python 3.12+。Windows/macOS 的 `python` 命令名可能不同，请替换为本机解释器。

规划 API 保持 `POST /api/agent/plans/`，body 如下：

```json
{"message":"不要训练模型，只导出已有报告","run_id":"已有任务编号"}
```

新增返回字段：

- `direct_skill_ids` / `direct_count`：真正命中的用户业务目标，**评估准确率应看这些字段**。
- `steps[].selection_kind`：`direct`、`dependency`、`governance`；依赖和治理步骤不等于用户请求了这些技能。
- `analysis.routing_source`：训练模型或专家证据规则的来源；明确动作语法的覆盖记录在每条 decision 的 reason 中。
- `analysis.routing_decisions`：候选、原始模型得分、词汇覆盖、拒绝原因和模型版本。
- `analysis.needs_clarification` / `excluded_skills` / `dependency_conflicts`：未知、否定与依赖冲突。

模型 softmax 得分尚未做概率校准；它不是“正确率置信区间”。明确动作规则的得分标记为 `explicit_action_rule`，保留原模型分数供排查。

## 重新训练

仅训练机器需要额外安装训练依赖：

```bash
python -m pip install -r training/skill_router/requirements.txt
python training/skill_router/train.py
python training/skill_router/evaluate.py
python manage.py test core.test_skill_routing core.tests.AgentChatTests --noinput
```

`train.py` 只读取 train 和 validation；`evaluate.py` 不修改模型。特征为字符 2–4 gram TF-IDF，分类器为多类逻辑回归，固定种子42。交付模型选择 C=20，概率阈值0.12、首二候选差值0.03、已知二元字符覆盖率0.20。这些阈值用验证集选择，不应当作普适常数。

同一个测试集反复用于改代码、增补训练例后，就不能再作为独立验收集。此时请建立新的留出测试版本，并保留旧版结果作为回归记录。

## 加入真实误调样本

不要把错误预测直接当作真标签。先由懂业务的人员确认正确 skill，然后按下面格式加入训练数据：

```json
{"id":"real-0001","group":"session-001-intent-A","text":"现场用户原话","labels":["正确的skill_id"],"source":"human_labeled_real_request","split":"train"}
```

无相关业务技能用 `"labels": []`。每个训练样本只标注一个原子目标；多目标请求先拆成原子句，同时把完整句加入多意图回归。**同一会话、同一意图模板的改写必须放在同一分组、同一数据划分**，不能混入训练与测试。建议记录真实误调频次和错误类型，优先补齐易混对：选阶/训练、模型基准/实验历史、报告撰写/报告下载、模型诊断/绘图。

`build_data.py` 用来重建本次合成数据，会覆盖 data 内三个文件；加入真实数据后不要直接运行它，先备份或在单独目录构建。

## 执行范围与当前边界

- “只清洗”在 cleaning 阶段结束；“只训练系统辨识模型”在 modeling 阶段结束，不自动启动闭环寻优。
- 下载已有产物读取当前结果，不重新训练或撰写报告。
- 否定、假设、引用中的执行字样不授权重跑；无法识别时不再兜底生成报告。
- 保留原工程的专家证据组合规则，所以部分专家问答仍会多选相关证据技能；验收报告严格将它们计作额外选择。
- 原工程的算法接口按阶段打包，并没有30个独立算法执行器。时滞单独计算、独立绘图、仿真生成等尚未独立接入聊天执行；现在会明确显示已规划/读取证据，不会伪称执行，也不会因此重跑全流程。
- `execute_skill_plan` 是编排与证据记录接口；算法是否真的运行应看聊天返回的 `executed`、`execution_scope` 和流水线产物。
- 训练脚本当前为单目标分类；多意图通过分句组合，不是通用语义理解模型。未知表述和上下文仍可能误判。

## 已知原包问题

全后端65项测试中，旧历史证据桥接测试1项失败：原 ZIP 的 `integrations/agent_control/` 为空，缺少硬编码引用的历史运行JSON。没有伪造该证据或修改测试来掩盖它。路由相关43项测试全部通过。详情见 `reports/preexisting-failure.json` 和 `reports/full-regression.log`。
