from django.db import migrations


KEEP_SCENARIOS = ("钢铁高炉铁水质量预测", "炼油脱丁烷塔", "工业干燥器")


def prune(apps, schema_editor):
    ScenarioTemplate = apps.get_model("core", "ScenarioTemplate")
    ScenarioTemplate.objects.exclude(scenario_name__in=KEEP_SCENARIOS).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0008_seed_blast_furnace_scenario")]
    operations = [migrations.RunPython(prune, migrations.RunPython.noop)]
