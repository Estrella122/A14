from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0004_optimization_early_stopping'),
    ]

    operations = [
        migrations.AlterField(
            model_name='optimizationstudy',
            name='total_rounds',
            field=models.PositiveIntegerField(default=12, verbose_name='总轮次'),
        ),
        migrations.AlterField(
            model_name='optimizationstudy',
            name='min_rounds',
            field=models.PositiveIntegerField(default=8, verbose_name='最少轮次'),
        ),
    ]
