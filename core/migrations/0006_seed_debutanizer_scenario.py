from django.db import migrations


def seed(apps, schema_editor):
    ScenarioTemplate = apps.get_model("core", "ScenarioTemplate")
    ScenarioTemplate.objects.update_or_create(
        scenario_name="炼油脱丁烷塔",
        defaults={
            "industry_type": "石油炼制",
            "input_variables": "塔顶温度、塔顶压力、回流流量、后续流程流量、第六塔板温度、塔底温度A、塔底温度B",
            "output_variables": "塔底丁烷含量",
            "controllable_variables": "回流流量、后续流程流量",
            "disturbance_variables": "塔顶压力、上下游工况",
            "quality_variables": "塔底丁烷含量",
            "modeling_objective": "建立脱丁烷塔塔底丁烷含量软测量模型，并验证多步预测和自由仿真。",
            "evaluation_metrics": "R2、RMSE、MAE、持续值基线改善、自由仿真稳定性",
            "variable_unit_rules": "公开基准数据为归一化量；时滞单位为sample，不换算为物理时间。",
            "outlier_rules": "按归一化量程、因果滚动统计和连续异常段联合识别。",
            "report_template": "炼油脱丁烷塔软测量验收报告模板",
        },
    )


def unseed(apps, schema_editor):
    apps.get_model("core", "ScenarioTemplate").objects.filter(scenario_name="炼油脱丁烷塔").delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0005_optimization_stopping_defaults")]
    operations = [migrations.RunPython(seed, unseed)]
