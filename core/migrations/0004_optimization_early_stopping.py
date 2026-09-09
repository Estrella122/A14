from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0003_closed_loop_optimization'),
    ]

    operations = [
        migrations.AddField(
            model_name='optimizationstudy',
            name='run_mode',
            field=models.CharField(default='auto_converge', max_length=30, verbose_name='运行模式'),
        ),
        migrations.AddField(
            model_name='optimizationstudy',
            name='min_rounds',
            field=models.PositiveIntegerField(default=5, verbose_name='最少轮次'),
        ),
        migrations.AddField(
            model_name='optimizationstudy',
            name='early_stopping_patience',
            field=models.PositiveIntegerField(default=3, verbose_name='早停耐心值'),
        ),
        migrations.AddField(
            model_name='optimizationstudy',
            name='min_improvement',
            field=models.DecimalField(decimal_places=4, default=Decimal('0.2'), max_digits=8, verbose_name='最小有效改善'),
        ),
        migrations.AddField(
            model_name='optimizationstudy',
            name='no_improvement_rounds',
            field=models.PositiveIntegerField(default=0, verbose_name='连续无改善轮数'),
        ),
        migrations.AddField(
            model_name='optimizationstudy',
            name='stop_reason',
            field=models.CharField(blank=True, max_length=255, verbose_name='停止原因'),
        ),
        migrations.AddField(
            model_name='optimizationstudy',
            name='early_stopped',
            field=models.BooleanField(default=False, verbose_name='是否提前收敛'),
        ),
    ]
