from django.db import migrations


SCENARIO_NAME = "钢铁高炉铁水质量预测"


def seed_blast_furnace_scenario(apps, schema_editor):
    ScenarioTemplate = apps.get_model("core", "ScenarioTemplate")
    ScenarioTemplate.objects.update_or_create(
        scenario_name=SCENARIO_NAME,
        defaults={
            "industry_type": "钢铁冶金",
            "input_variables": "鼓风流量、富氧流量、热风温度、热风压力、压差、炉顶煤气成分、炉顶及炉身温度、矿焦比",
            "output_variables": "铁水硅含量（Si）",
            "controllable_variables": "鼓风流量、富氧流量、热风温度、矿焦比",
            "disturbance_variables": "炉料与焦炭性质、炉况波动、化验采样间隔",
            "quality_variables": "铁水硅含量、化验数据龄期、化验新鲜度",
            "modeling_objective": "利用高炉传感器历史数据预测铁水硅含量，优选高信息量动态数据并形成可复现的离线闭环寻优证据。",
            "evaluation_metrics": "R2、RMSE、MAE、动态段覆盖率、化验对齐龄期、残差白噪声检验",
            "variable_unit_rules": "流量: m³/min 或 m³/h; 压力: kgf/cm²; 温度: ℃; 成分: %; 化验龄期: min",
            "outlier_rules": "工艺上下限与稳健统计联合识别；铁水化验值只允许向后因果对齐，禁止使用未来化验结果。",
            "report_template": "钢铁高炉铁水硅含量预测与数据优选报告模板",
        },
    )


def unseed_blast_furnace_scenario(apps, schema_editor):
    ScenarioTemplate = apps.get_model("core", "ScenarioTemplate")
    ScenarioTemplate.objects.filter(scenario_name=SCENARIO_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0007_seed_industrial_dryer_scenario")]

    operations = [migrations.RunPython(seed_blast_furnace_scenario, unseed_blast_furnace_scenario)]
