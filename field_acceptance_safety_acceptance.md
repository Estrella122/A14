# 字段接受安全验收

| 场景 | 列数 | 旧接受 | 旧错接受 | 新接受 | 新错接受 | review | reject | 新增 false reject |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blast_furnace | 32 | 32 | 0 | 32 | 0 | 0 | 0 | 0 |
| debutanizer_column | 43 | 25 | 24 | 1 | 0 | 38 | 4 | 0 |
| industrial_dryer | 23 | 0 | 0 | 0 | 0 | 2 | 21 | 0 |

三场景 GT 集新增 false reject=0；指定 bottom_temp_a、top temp [degC]、tray_6_temperature 正例通过。Reboiler o/l Temp、Feed Flow to DB 维持 review/reject；高置信坏 alias、错通道、错误方向、未知关键单位、人工去重恢复、跨场景元数据、错误 inverse binding 均有专项测试。

core/test_final_field_acceptance.py 新增 13 项测试；既有 trained_model_auto 门禁与 Ground Truth、OOD、清洗安全测试保留。没有删除失败用例或新增 skip。4 条旧断言原本要求匿名 U 字段被接受，已改为精确验证 8 个字段受阻及场景不能 confirmed；不是削弱安全标准。

既有三项数据许可/真实文件缺口 skip 保留。没有训练新模型，没有调整阈值或 alias/required；现有 safety gate 对未知源仍不是事实鉴定器。完整 trace 位于 datasets/field_acceptance_safety/after.json。
