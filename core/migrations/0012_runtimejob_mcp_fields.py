from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_knowledgedocument_routingfeedback_knowledgeentity_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="runtimejob",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "排队中"),
                    ("running", "运行中"),
                    ("completed", "已完成"),
                    ("blocked", "已阻断"),
                    ("failed", "失败"),
                    ("cancelled", "已取消"),
                ],
                db_index=True,
                default="queued",
                max_length=20,
                verbose_name="任务状态",
            ),
        ),
        migrations.AddField(model_name="runtimejob", name="request_id", field=models.CharField(blank=True, db_index=True, max_length=64, verbose_name="请求ID")),
        migrations.AddField(model_name="runtimejob", name="caller_id", field=models.CharField(blank=True, db_index=True, max_length=160, verbose_name="调用方")),
        migrations.AddField(model_name="runtimejob", name="tool_name", field=models.CharField(blank=True, db_index=True, max_length=100, verbose_name="工具名称")),
        migrations.AddField(model_name="runtimejob", name="idempotency_fingerprint", field=models.CharField(blank=True, max_length=64, null=True, unique=True, verbose_name="幂等指纹")),
        migrations.AddField(model_name="runtimejob", name="current_stage", field=models.CharField(blank=True, max_length=40, verbose_name="当前阶段")),
        migrations.AddField(model_name="runtimejob", name="progress", field=models.JSONField(blank=True, default=dict, verbose_name="任务进度")),
        migrations.AddField(model_name="runtimejob", name="error_code", field=models.CharField(blank=True, max_length=64, verbose_name="错误码")),
        migrations.AddField(model_name="runtimejob", name="cancel_requested_at", field=models.DateTimeField(blank=True, null=True, verbose_name="取消请求时间")),
    ]
