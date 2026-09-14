# 三场景真实Pipeline验收

图中第2项：PARTIAL。没有完成三场景真实数据Pipeline。

|Scene|Data source|Data confidence|Pipeline|Modeling|
|---|---|---|---|---|
|blast_furnace|固定blast_furnace_real_720h.csv|DERIVED / REAL|PARTIAL（SNR有不可估计值）|PARTIAL|
|debutanizer_column|大学Fortuna/工厂候选|PUBLIC_REAL_PROCESS/BENCHMARK候选；契约不通过|UNAVAILABLE|NOT_EXECUTED|
|industrial_dryer|DAISY、公开实验、烟草线索|PUBLIC_REAL_PROCESS/PUBLIC_EXPERIMENT候选；现有可执行仅SYNTHETIC|PARTIAL|NOT_EXECUTED（真实数据）|

通用架构/同Registry/同Executor/同算法继续沿用PASS，本轮未修改。两个目标场景无候选通过全部预检，12数值节点都未启动，不能标DONE。

高炉仅执行一次固定对照；新run_id、12节点回执、参数、metrics、warnings、artifacts及模型完整诊断见three_scene_real_runtime.json/scenes[0]/receipt。模型稳定且单步略优于persistence，但残差ACF超参考界限，不能把诊断status success当Modeling PASS。没有补SNR null或调参。

真实数据模型验收仍遵循冻结后只测一次，缺数据不输出假测试指标。不对训练/验证读取test或根据test换数据/参数。新增测试验证缺数据时的拒绝分支，不能将这类通过计作12数值执行通过。

## 高炉固定实测回执摘要

run_id：`scene_2f9464672c69`；skill_run_id：`skillrun_fd4da9b040e2`。对照：`{"dataset_sha256": true, "skill_ids": true, "executor_modules": true, "metrics": true}`。

```json
{
  "validation_rmse": 0.06441828005591495,
  "test_rmse": 0.04643078209424044,
  "persistence_rmse": 0.048363701461402016,
  "relative_improvement_pct": 3.996632409750933,
  "model_family": "AR",
  "candidate_count": 12,
  "stable_ar_poles": true,
  "test_10_step_rmse": 0.08094748571209436,
  "test_10_step_persistence": 0.09991300563816591,
  "free_simulation": {
    "conditional_on_observed_inputs": true,
    "diverged": false,
    "metrics": {
      "n_samples": 105.0,
      "num_params": 2.0,
      "r2": -0.5909183181066882,
      "adjusted_r2": -0.6221127949323095,
      "rmse": 0.0819943247809784,
      "mae": 0.06575011251525816,
      "mse": 0.006723069296288569,
      "sse": 0.7059222761102998,
      "fpe": 0.006984159366047349,
      "aic": -521.2321012612256,
      "bic": -515.9241805609105
    }
  },
  "residual": {
    "acf_max_abs": 0.2581643800853005,
    "heuristic_95pct_bound": 0.1912764142979125,
    "whiteness_test": "not_performed; ACF is diagnostic only"
  },
  "executor_invoked_count": 12
}
```

训练/验证按现有固定协议，结构冻结后一次test。本轮未改训练/验证算法，完整后端会重新运行已有测试泄漏防护。白噪声检验当前未实现，只有残差ACF启发式界限，保留not_performed。

## 测试及修改范围

新增core/test_real_dataset_acceptance.py十项来源/契约/未执行保护/MD高炉回执/hash测试全部通过；两个目标场景pipeline测试验证拒绝分支，不当作正向数值成功。完整core：335项，332通过、3原有skip、0 failures、0 errors。没有新增skip，也没有移除尚未满足数据条件的skip。测试日志在runtime/data_validation/real_search。

本轮新增7份交付、10项测试、源缓存SOURCE.md/transformation_manifest.json、候选下载和高炉单次实际产物。没有创建新pipeline或修改现有架构/算法/场景契约。没有向GitHub提交或上传数据。

## 最终问题回答

1–4：有真实来源脱丁烷候选（Coimbra/Fortuna；另有作者声明工厂数据），但当前物理字段契约未通过，12 Skill未执行。
5–8：有真实工业干燥器候选（DAISY、公开实验及烟草生产线线索），当前契约不匹配或原文件未取得，12 Skill未执行。
9：高炉12个Executor实际执行，对照指标完全一致；保留SNR null和模型诊断边界，Pipeline/Modeling PARTIAL。
10–11：三个场景尚未全部完成真实数据Pipeline，图中第2项PARTIAL。
