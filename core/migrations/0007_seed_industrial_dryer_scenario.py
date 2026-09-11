from django.db import migrations


def seed(apps, schema_editor):
    ScenarioTemplate = apps.get_model("core", "ScenarioTemplate")
    ScenarioTemplate.objects.update_or_create(
        scenario_name="工业干燥器",
        defaults={
            "industry_type": "流程工业",
            "input_variables": "热风入口温度、干燥风量、湿料进料量",
            "output_variables": "产品含水率、产品出口温度、排风湿度",
            "controllable_variables": "热风入口温度、干燥风量、湿料进料量",
            "disturbance_variables": "进料初始含水率、环境温湿度、原料粒径",
            "quality_variables": "产品含水率",
            "modeling_objective": "提取快速动态段并建立3输入3输出ARX模型组，完成各输出响应分析。",
            "evaluation_metrics": "各输出R2、RMSE、MAE、持续值基线改善、多步预测、自由仿真稳定性",
            "variable_unit_rules": "10秒采样；温度degC、风量Nm3/h、进料t/h、湿度与含水率percent。",
            "outlier_rules": "按物理边界、因果滚动统计、变化率和连续异常段联合识别。",
            "report_template": "工业干燥器MIMO辨识与响应分析验收报告模板",
        },
    )


def unseed(apps, schema_editor):
    apps.get_model("core", "ScenarioTemplate").objects.filter(scenario_name="工业干燥器").delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0006_seed_debutanizer_scenario")]
    operations = [migrations.RunPython(seed, unseed)]
