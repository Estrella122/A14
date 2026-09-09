from django.db import migrations


def seed_scenario_templates(apps, schema_editor):
    ScenarioTemplate = apps.get_model('core', 'ScenarioTemplate')
    templates = [
        {
            'scenario_name': '钢厂加热炉',
            'industry_type': '钢铁冶金',
            'input_variables': '煤气流量、空气流量、空燃比、炉膛压力、板坯速度、入炉温度',
            'output_variables': '出炉温度、炉温均匀性、能耗指标',
            'controllable_variables': '煤气流量、空气流量、各段炉温设定值',
            'disturbance_variables': '板坯规格、入炉温度、生产节奏、炉膛压力',
            'quality_variables': '出炉温度、温度偏差、氧化烧损',
            'modeling_objective': '建立加热炉温度响应模型，优选高动态建模数据，支撑 APC 控制器整定。',
            'evaluation_metrics': 'R2、RMSE、MAE、拟合度、动态段覆盖率',
            'variable_unit_rules': '温度: ℃; 流量: Nm³/h; 压力: Pa; 速度: m/min',
            'outlier_rules': '3σ 规则叠加工艺上下限，连续异常段进入剔除候选。',
            'report_template': '加热炉 APC 建模数据优选报告模板',
        },
        {
            'scenario_name': '污水处理曝气',
            'industry_type': '环保水处理',
            'input_variables': '曝气风量、回流比、进水流量、进水 COD、氨氮、温度',
            'output_variables': 'DO 浓度、出水氨氮、能耗指标',
            'controllable_variables': '曝气风量、鼓风机频率、回流比',
            'disturbance_variables': '进水负荷、进水温度、进水流量',
            'quality_variables': 'DO 浓度、出水氨氮、总氮',
            'modeling_objective': '建立曝气过程 DO 与出水指标预测模型，支撑节能优化控制。',
            'evaluation_metrics': 'R2、RMSE、MAE、能耗下降率、出水达标率',
            'variable_unit_rules': 'DO: mg/L; 流量: m³/h; 频率: Hz; 浓度: mg/L',
            'outlier_rules': '按传感器量程、3σ 与持续时间规则联合识别异常。',
            'report_template': '污水处理曝气 APC 建模数据优选报告模板',
        },
        {
            'scenario_name': '电厂锅炉燃烧',
            'industry_type': '电力能源',
            'input_variables': '给煤量、一次风量、二次风量、氧量、负荷、磨煤机状态',
            'output_variables': '主汽温度、NOx 排放、锅炉效率',
            'controllable_variables': '给煤量、风门开度、配风比例、氧量设定值',
            'disturbance_variables': '机组负荷、煤质、环境温度',
            'quality_variables': 'NOx 排放、主汽温度、锅炉效率',
            'modeling_objective': '建立燃烧效率与排放响应模型，支撑低氮燃烧和经济运行优化。',
            'evaluation_metrics': 'R2、RMSE、MAE、NOx 误差、效率提升幅度',
            'variable_unit_rules': '负荷: MW; 流量: t/h; 温度: ℃; 氧量: %; 排放: mg/Nm³',
            'outlier_rules': '按负荷区间分层识别异常，并剔除启停炉非稳态异常段。',
            'report_template': '电厂锅炉燃烧 APC 建模数据优选报告模板',
        },
        {
            'scenario_name': '化工反应釜',
            'industry_type': '化工过程',
            'input_variables': '进料流量、夹套温度、搅拌转速、催化剂加入量、反应压力',
            'output_variables': '反应温度、转化率、选择性、产品质量',
            'controllable_variables': '进料流量、夹套温度、搅拌转速、催化剂加入量',
            'disturbance_variables': '原料批次、环境温度、进料浓度',
            'quality_variables': '转化率、选择性、产品质量指标',
            'modeling_objective': '建立反应过程动态辨识模型，支撑质量稳定和闭环寻优。',
            'evaluation_metrics': 'R2、RMSE、MAE、拟合度、质量达标率',
            'variable_unit_rules': '温度: ℃; 压力: MPa; 流量: kg/h; 转速: rpm; 浓度: mol/L',
            'outlier_rules': '结合反应安全边界、批次阶段和 3σ 规则识别异常。',
            'report_template': '化工反应釜 APC 建模数据优选报告模板',
        },
    ]

    for template in templates:
        ScenarioTemplate.objects.update_or_create(
            scenario_name=template['scenario_name'],
            defaults=template,
        )


def unseed_scenario_templates(apps, schema_editor):
    ScenarioTemplate = apps.get_model('core', 'ScenarioTemplate')
    ScenarioTemplate.objects.filter(
        scenario_name__in=['钢厂加热炉', '污水处理曝气', '电厂锅炉燃烧', '化工反应釜']
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_scenario_templates, unseed_scenario_templates),
    ]
