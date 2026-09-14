# 最终回归报告

日期：2026-09-14。图中第2项：PARTIAL。两场景数据契约不通过，未执行其12 Skill；状态断言通过不代表真实数值Pipeline通过。

## 检查结果

| 检查 | 结果 |
| --- | --- |
| manage.py test core | 396项，393通过、3已有skip，0 failures/errors；23.864秒 |
| 本轮12个命名验收测试 | 全部通过；两个缺数据场景验证FAIL/UNAVAILABLE边界，未新增skip |
| npm test | 32通过，0失败、0跳过 |
| npm run lint | PASS，43个JS/Vue文件 |
| npm run build | PASS |
| git diff --check | PASS |
| 受保护文件hash | 118/118未变 |
| 实际可访问候选原文件hash | 12份复核一致 |
| 高炉固定回归 | 本轮专门运行一次，scene_8f53099c7ed4；hash/skill_ids/executor_modules/metrics均与固定基线一致 |

首次测试中新增test_md_mode_only误要求所有节点execute，导致1失败。按任务第22节和现有SKILL.md修正为逐节点核对其声明的execute/read模式，仍要求executor_invoked和当前run内产物溯源。随后完整core重跑得到上述结果，没有修改Runtime或放宽业务门禁。

## 已有skip说明

- core/test_debutanizer.py：上游数据缺明确可再分发许可，本地正式数据不可用。
- core/test_debutanizer_contract.py：缺物理量数据或可信逆缩放元数据，不能执行真实数值验收。
- core/test_three_scene_final.py：缺合格物理量源文件，完整数值验收未通过。

这些skip仍是数据限制，不能计入三场景真实Pipeline完成。新增最终收尾测试没有skip。

## 本轮修改范围

- tools/precheck_real_dataset.py：仅增加重复时间戳数量诊断，不修改候选准入判断。
- tools/write_real_closeout_reports.py：汇总现有契约、候选、回执及最终规范。
- core/test_final_real_closeout.py：12项最终验收断言。
- 12份最终交付文件及datasets/real_validation/closeout证据、预检结果。
- three_scene_final_real_runtime.json保存本次高炉回执及两场景UNAVAILABLE状态。

禁止改动范围由protected_hashes.json核对；118个文件未改变。保留工作区已有修改，不将之前改动归入本轮。未训练字段Agent，NOT_NEEDED_CURRENTLY。

## Git同步

开始与结束均fetch origin。HEAD eb240e8922ce953665844380fabb5c0c575718c9，HEAD...origin/main为0/0。已跟当前远端基线核对，无新增远端提交需要合并；本轮工作仍在本地，未commit/push。

## 证据与限制

日志位于datasets/real_validation/closeout/validation/；完整高炉回执见three_scene_final_real_runtime.json。数据来源清单、契约及hash是本地验收依赖，未核实许可的原始数据不发布。烟草归档Apache-2.0声明不等同于取得完整工厂原始数据授权。当前搜索停止条件为C+D，详见real_data_search_stop_report.md。
