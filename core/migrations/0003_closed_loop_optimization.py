import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0002_seed_scenario_templates'),
    ]

    operations = [
        migrations.CreateModel(
            name='OptimizationStudy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project_code', models.CharField(db_index=True, max_length=120, verbose_name='项目编码')),
                ('project_name', models.CharField(max_length=200, verbose_name='项目名称')),
                ('dataset_mode', models.CharField(default='synthetic_benchmark', max_length=80, verbose_name='数据集模式')),
                ('status', models.CharField(choices=[('ready', '待运行'), ('running', '运行中'), ('completed', '已完成'), ('accepted', '已采纳'), ('failed', '失败')], default='ready', max_length=30, verbose_name='任务状态')),
                ('total_rounds', models.PositiveIntegerField(default=8, verbose_name='总轮次')),
                ('current_round', models.PositiveIntegerField(default=0, verbose_name='当前轮次')),
                ('search_space', models.JSONField(default=dict, verbose_name='搜索空间')),
                ('objective_weights', models.JSONField(default=dict, verbose_name='目标权重')),
                ('constraints', models.JSONField(default=dict, verbose_name='约束条件')),
                ('initial_candidate', models.JSONField(default=dict, verbose_name='初始候选参数')),
                ('random_seed', models.PositiveIntegerField(default=20260731, verbose_name='随机种子')),
                ('error_message', models.TextField(blank=True, verbose_name='错误信息')),
                ('started_at', models.DateTimeField(blank=True, null=True, verbose_name='开始时间')),
                ('finished_at', models.DateTimeField(blank=True, null=True, verbose_name='完成时间')),
                ('accepted_at', models.DateTimeField(blank=True, null=True, verbose_name='采纳时间')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('accepted_run', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='core.optimizationrun', verbose_name='已采纳轮次')),
                ('best_run', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='core.optimizationrun', verbose_name='最优轮次')),
            ],
            options={
                'verbose_name': '闭环寻优任务',
                'verbose_name_plural': '闭环寻优任务',
                'db_table': 'optimization_studies',
                'ordering': ('-created_at',),
            },
        ),
        migrations.AlterField(
            model_name='optimizationrun',
            name='file',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.datafile', verbose_name='文件ID'),
        ),
        migrations.AddField(
            model_name='optimizationrun',
            name='study',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='iterations', to='core.optimizationstudy', verbose_name='寻优任务'),
        ),
        migrations.AddField(
            model_name='optimizationrun',
            name='model_fit',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=8, verbose_name='模型拟合度'),
        ),
        migrations.AddField(
            model_name='optimizationrun',
            name='coverage_ratio',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=8, verbose_name='数据覆盖率'),
        ),
        migrations.AddField(
            model_name='optimizationrun',
            name='cost_score',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=8, verbose_name='计算成本'),
        ),
        migrations.AddField(
            model_name='optimizationrun',
            name='candidate_parameters',
            field=models.JSONField(default=dict, verbose_name='候选参数与诊断信息'),
        ),
        migrations.AddField(
            model_name='optimizationrun',
            name='is_best',
            field=models.BooleanField(default=False, verbose_name='是否最优'),
        ),
        migrations.AddField(
            model_name='optimizationrun',
            name='duration_ms',
            field=models.PositiveIntegerField(default=0, verbose_name='计算耗时毫秒'),
        ),
        migrations.AddConstraint(
            model_name='optimizationrun',
            constraint=models.UniqueConstraint(fields=('study', 'round_number'), name='unique_study_round'),
        ),
    ]
