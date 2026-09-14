# 真实数据阶段全量回归

GitHub：开始与结束均 fetch；main=eb240e8，与 origin/main 差异0/0。本轮未提交/推送，保留此前本地修改。

| 检查 | 结果 |
| --- | --- |
| manage.py test core | 384 tests，381 passed，3 原有 skipped，0 failure/error |
| 本轮新增预检测试 | 3 passed，0 skip |
| npm test | 32 passed，0 skipped |
| npm run lint | PASS，43 JS/Vue 文件 |
| npm run build | PASS |
| git diff --check | PASS |
| 高炉固定真实回归 | run scene_7f50c10fdde5；12 Executor 调用；hash/Skill/module/metrics 全一致 |
| 新真实数据预检 | 8个代表源/子集生成JSON，只有固定高炉ELIGIBLE |

旧skip是再分发许可/真实数值源不足，不计为三场景实际Pipeline完成。本轮没有新增skip，也未修改既有业务测试预期。

新增代码：tools/precheck_real_dataset.py、tools/run_final_real_prechecks.py、tools/write_real_final_reports.py、core/test_real_dataset_precheck.py。新增库存/候选/预检/许可/需求/验收文档及三场景收据。没有修改Runtime、Loader、Registry、Planner、SceneContext、12算法、安全门禁、required、alias、阈值或高炉模型。

可复现预检（项目根目录）：

```bash
.venv/bin/python tools/precheck_real_dataset.py SOURCE.csv --scene debutanizer_column --metadata source_metadata.json --output dataset_precheck.json
.venv/bin/python tools/run_final_real_prechecks.py
.venv/bin/python tools/write_real_final_reports.py
```

XLSX检查使用本地openpyxl读取，未执行下载归档中的train.py或任何外部模型代码。此依赖只安装于本地venv；新工具读取XLSX需要openpyxl，CSV预检不依赖它。metadata必须由源证据支持，工具不自动认证其真伪。

原文件不覆盖。没有合格脱丁烷/干燥数据，故没有准备假processed CSV或inverse transformation manifest。原有已通过的高炉转换证据继续复用。新zip/xlsx的下载/成员提取记录见datasets/real_validation/tobacco_acquisition_manifest.json。

本轮未进行浏览器E2E或生产服务验收；结果为自动测试、真实文件预检和固定真实数值Pipeline。日志与哈希：datasets/real_validation/validation/。
