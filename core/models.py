from decimal import Decimal

from django.db import models


class ScenarioTemplate(models.Model):
    scenario_name = models.CharField('场景名称', max_length=100, unique=True)
    industry_type = models.CharField('行业类型', max_length=100)
    input_variables = models.TextField('输入变量')
    output_variables = models.TextField('输出变量')
    controllable_variables = models.TextField('可控变量')
    disturbance_variables = models.TextField('扰动变量')
    quality_variables = models.TextField('质量变量')
    modeling_objective = models.TextField('建模目标')
    evaluation_metrics = models.TextField('评价指标')
    variable_unit_rules = models.TextField('变量单位规则')
    outlier_rules = models.TextField('异常值规则')
    report_template = models.TextField('报告模板')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'scenario_templates'
        verbose_name = '场景模板'
        verbose_name_plural = '场景模板'

    def __str__(self):
        return self.scenario_name


class DataFile(models.Model):
    file_name = models.CharField('文件名称', max_length=255)
    scenario = models.ForeignKey(ScenarioTemplate, verbose_name='场景ID', on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField('上传时间', auto_now_add=True)
    row_count = models.PositiveIntegerField('数据行数')
    variable_count = models.PositiveIntegerField('变量数量')
    time_range = models.CharField('时间范围', max_length=255)
    sampling_period = models.CharField('采样周期', max_length=50)
    missing_value_ratio = models.DecimalField('缺失值比例', max_digits=6, decimal_places=3)
    outlier_ratio = models.DecimalField('异常值比例', max_digits=6, decimal_places=3)
    file_path = models.CharField('文件路径', max_length=500)
    processing_status = models.CharField('处理状态', max_length=50)

    class Meta:
        db_table = 'data_files'
        verbose_name = '工业时序数据文件'
        verbose_name_plural = '工业时序数据文件'

    def __str__(self):
        return self.file_name


class VariableMapping(models.Model):
    scenario = models.ForeignKey(ScenarioTemplate, verbose_name='场景ID', on_delete=models.CASCADE)
    original_field_name = models.CharField('原始字段名', max_length=120)
    standard_variable_name = models.CharField('标准变量名', max_length=160)
    variable_role = models.CharField('变量角色', max_length=50)
    variable_unit = models.CharField('变量单位', max_length=50)
    upper_limit = models.DecimalField('上限', max_digits=14, decimal_places=4, null=True, blank=True)
    lower_limit = models.DecimalField('下限', max_digits=14, decimal_places=4, null=True, blank=True)
    is_required = models.BooleanField('是否必填', default=True)
    description = models.TextField('说明', blank=True)

    class Meta:
        db_table = 'variable_mappings'
        verbose_name = '统一变量映射'
        verbose_name_plural = '统一变量映射'

    def __str__(self):
        return f'{self.original_field_name} -> {self.standard_variable_name}'


class StandardCheck(models.Model):
    file = models.ForeignKey(DataFile, verbose_name='文件ID', on_delete=models.CASCADE)
    check_item = models.CharField('检查项', max_length=120)
    check_result = models.CharField('检查结果', max_length=50)
    problem_description = models.TextField('问题说明', blank=True)
    repair_suggestion = models.TextField('修复建议', blank=True)
    checked_at = models.DateTimeField('检查时间', auto_now_add=True)

    class Meta:
        db_table = 'standard_checks'
        verbose_name = '数据标准化检查'
        verbose_name_plural = '数据标准化检查'

    def __str__(self):
        return f'{self.file_id} - {self.check_item}'


class CleaningRecord(models.Model):
    file = models.ForeignKey(DataFile, verbose_name='文件ID', on_delete=models.CASCADE)
    missing_value_method = models.CharField('缺失值处理方式', max_length=120)
    outlier_threshold = models.CharField('异常值阈值', max_length=80)
    resampling_period = models.CharField('重采样周期', max_length=50)
    before_cleaning_count = models.PositiveIntegerField('清洗前数据量')
    after_cleaning_count = models.PositiveIntegerField('清洗后数据量')
    missing_value_ratio = models.DecimalField('缺失值比例', max_digits=6, decimal_places=3)
    outlier_ratio = models.DecimalField('异常值比例', max_digits=6, decimal_places=3)
    cleaning_status = models.CharField('清洗状态', max_length=50)
    cleaned_at = models.DateTimeField('清洗时间', auto_now_add=True)

    class Meta:
        db_table = 'cleaning_records'
        verbose_name = '数据清洗记录'
        verbose_name_plural = '数据清洗记录'

    def __str__(self):
        return f'{self.file_id} - {self.cleaning_status}'


class DynamicSegment(models.Model):
    file = models.ForeignKey(DataFile, verbose_name='文件ID', on_delete=models.CASCADE)
    start_time = models.DateTimeField('开始时间')
    end_time = models.DateTimeField('结束时间')
    dynamic_score = models.DecimalField('动态得分', max_digits=8, decimal_places=3)
    snr_score = models.DecimalField('信噪比得分', max_digits=8, decimal_places=3)
    integrity_score = models.DecimalField('完整性得分', max_digits=8, decimal_places=3)
    abnormal_ratio = models.DecimalField('异常比例', max_digits=6, decimal_places=3)
    overall_score = models.DecimalField('综合评分', max_digits=8, decimal_places=3)
    selected_for_modeling = models.BooleanField('是否入选建模数据', default=False)

    class Meta:
        db_table = 'dynamic_segments'
        verbose_name = '动态数据段'
        verbose_name_plural = '动态数据段'

    def __str__(self):
        return f'{self.file_id} - {self.start_time}'


class LagAnalysisResult(models.Model):
    file = models.ForeignKey(DataFile, verbose_name='文件ID', on_delete=models.CASCADE)
    input_variable = models.CharField('输入变量', max_length=160)
    output_variable = models.CharField('输出变量', max_length=160)
    optimal_lag = models.CharField('最优时滞', max_length=80)
    correlation_score = models.DecimalField('相关性得分', max_digits=8, decimal_places=4)
    compensation_method = models.CharField('补偿方式', max_length=120)
    analyzed_at = models.DateTimeField('分析时间', auto_now_add=True)

    class Meta:
        db_table = 'lag_analysis_results'
        verbose_name = '时滞分析结果'
        verbose_name_plural = '时滞分析结果'

    def __str__(self):
        return f'{self.input_variable} -> {self.output_variable}'


class CollinearityResult(models.Model):
    file = models.ForeignKey(DataFile, verbose_name='文件ID', on_delete=models.CASCADE)
    variable_a = models.CharField('变量A', max_length=160)
    variable_b = models.CharField('变量B', max_length=160)
    correlation_coefficient = models.DecimalField('相关系数', max_digits=8, decimal_places=4)
    collinearity_level = models.CharField('共线性等级', max_length=50)
    processing_method = models.CharField('处理方式', max_length=120)
    is_retained = models.BooleanField('是否保留', default=True)
    analyzed_at = models.DateTimeField('分析时间', auto_now_add=True)

    class Meta:
        db_table = 'collinearity_results'
        verbose_name = '共线性分析结果'
        verbose_name_plural = '共线性分析结果'

    def __str__(self):
        return f'{self.variable_a} / {self.variable_b}'


class ModelResult(models.Model):
    file = models.ForeignKey(DataFile, verbose_name='文件ID', on_delete=models.CASCADE)
    model_type = models.CharField('模型类型', max_length=100)
    training_data_source = models.CharField('训练数据来源', max_length=120)
    r2 = models.DecimalField('R2', max_digits=8, decimal_places=4)
    rmse = models.DecimalField('RMSE', max_digits=10, decimal_places=4)
    mae = models.DecimalField('MAE', max_digits=10, decimal_places=4)
    fitting_degree = models.DecimalField('拟合度', max_digits=8, decimal_places=4)
    model_parameters = models.TextField('模型参数')
    model_file_path = models.CharField('模型文件路径', max_length=500, blank=True)
    trained_at = models.DateTimeField('训练时间', auto_now_add=True)

    class Meta:
        db_table = 'model_results'
        verbose_name = '系统辨识模型结果'
        verbose_name_plural = '系统辨识模型结果'

    def __str__(self):
        return f'{self.model_type} - {self.training_data_source}'


class OptimizationStudy(models.Model):
    STATUS_CHOICES = (
        ('ready', '待运行'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('accepted', '已采纳'),
        ('failed', '失败'),
    )

    project_code = models.CharField('项目编码', max_length=120, db_index=True)
    project_name = models.CharField('项目名称', max_length=200)
    dataset_mode = models.CharField('数据集模式', max_length=80, default='synthetic_benchmark')
    status = models.CharField('任务状态', max_length=30, choices=STATUS_CHOICES, default='ready')
    total_rounds = models.PositiveIntegerField('总轮次', default=12)
    current_round = models.PositiveIntegerField('当前轮次', default=0)
    run_mode = models.CharField('运行模式', max_length=30, default='auto_converge')
    min_rounds = models.PositiveIntegerField('最少轮次', default=8)
    early_stopping_patience = models.PositiveIntegerField('早停耐心值', default=3)
    min_improvement = models.DecimalField('最小有效改善', max_digits=8, decimal_places=4, default=Decimal('0.2'))
    no_improvement_rounds = models.PositiveIntegerField('连续无改善轮数', default=0)
    stop_reason = models.CharField('停止原因', max_length=255, blank=True)
    early_stopped = models.BooleanField('是否提前收敛', default=False)
    search_space = models.JSONField('搜索空间', default=dict)
    objective_weights = models.JSONField('目标权重', default=dict)
    constraints = models.JSONField('约束条件', default=dict)
    initial_candidate = models.JSONField('初始候选参数', default=dict)
    random_seed = models.PositiveIntegerField('随机种子', default=20260731)
    best_run = models.ForeignKey(
        'OptimizationRun',
        verbose_name='最优轮次',
        related_name='+',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    accepted_run = models.ForeignKey(
        'OptimizationRun',
        verbose_name='已采纳轮次',
        related_name='+',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    error_message = models.TextField('错误信息', blank=True)
    started_at = models.DateTimeField('开始时间', null=True, blank=True)
    finished_at = models.DateTimeField('完成时间', null=True, blank=True)
    accepted_at = models.DateTimeField('采纳时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'optimization_studies'
        verbose_name = '闭环寻优任务'
        verbose_name_plural = '闭环寻优任务'
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.project_code} - {self.get_status_display()}'


class OptimizationRun(models.Model):
    file = models.ForeignKey(
        DataFile,
        verbose_name='文件ID',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    study = models.ForeignKey(
        OptimizationStudy,
        verbose_name='寻优任务',
        related_name='iterations',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    round_number = models.PositiveIntegerField('轮次')
    dynamic_segment_threshold = models.DecimalField('动态段阈值', max_digits=8, decimal_places=4)
    outlier_threshold = models.CharField('异常值阈值', max_length=80)
    collinearity_threshold = models.DecimalField('共线性阈值', max_digits=8, decimal_places=4)
    lag_search_range = models.CharField('时滞搜索范围', max_length=80)
    min_segment_length = models.CharField('最小数据段长度', max_length=80)
    model_r2 = models.DecimalField('模型R2', max_digits=8, decimal_places=4)
    model_fit = models.DecimalField('模型拟合度', max_digits=8, decimal_places=4, default=0)
    rmse = models.DecimalField('RMSE', max_digits=10, decimal_places=4)
    coverage_ratio = models.DecimalField('数据覆盖率', max_digits=8, decimal_places=4, default=0)
    cost_score = models.DecimalField('计算成本', max_digits=8, decimal_places=4, default=0)
    overall_score = models.DecimalField('综合得分', max_digits=8, decimal_places=4)
    review_result = models.CharField('评审结果', max_length=120)
    candidate_parameters = models.JSONField('候选参数与诊断信息', default=dict)
    is_best = models.BooleanField('是否最优', default=False)
    duration_ms = models.PositiveIntegerField('计算耗时毫秒', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'optimization_runs'
        verbose_name = '闭环寻优记录'
        verbose_name_plural = '闭环寻优记录'
        constraints = [
            models.UniqueConstraint(fields=('study', 'round_number'), name='unique_study_round'),
        ]

    def __str__(self):
        return f'{self.file_id} - 第{self.round_number}轮'


class AgentReview(models.Model):
    file = models.ForeignKey(DataFile, verbose_name='文件ID', on_delete=models.CASCADE)
    execution_agent_output = models.TextField('执行Agent输出')
    review_agent_conclusion = models.TextField('评审Agent结论')
    data_quality_result = models.CharField('数据质量结果', max_length=120)
    dynamic_segment_validity_result = models.CharField('动态段有效性结果', max_length=120)
    lag_compensation_result = models.CharField('时滞补偿结果', max_length=120)
    collinearity_processing_result = models.CharField('共线性处理结果', max_length=120)
    model_fitting_result = models.CharField('模型拟合度结果', max_length=120)
    report_integrity_result = models.CharField('报告完整性结果', max_length=120)
    modification_suggestions = models.TextField('修改建议', blank=True)
    is_passed = models.BooleanField('是否通过', default=False)
    reviewed_at = models.DateTimeField('评审时间', auto_now_add=True)

    class Meta:
        db_table = 'agent_reviews'
        verbose_name = 'Agent评审记录'
        verbose_name_plural = 'Agent评审记录'

    def __str__(self):
        return f'{self.file_id} - {self.is_passed}'


class ExportRecord(models.Model):
    file = models.ForeignKey(DataFile, verbose_name='文件ID', on_delete=models.CASCADE)
    export_type = models.CharField('导出类型', max_length=100)
    export_file_name = models.CharField('导出文件名', max_length=255)
    export_path = models.CharField('导出路径', max_length=500)
    exported_at = models.DateTimeField('导出时间', auto_now_add=True)
    export_status = models.CharField('导出状态', max_length=50)

    class Meta:
        db_table = 'export_records'
        verbose_name = '报告导出记录'
        verbose_name_plural = '报告导出记录'

    def __str__(self):
        return self.export_file_name


class RuntimeJob(models.Model):
    """Durable queue entry used by both pipeline and Agent workers."""

    STATUS_CHOICES = (
        ('queued', '排队中'), ('running', '运行中'), ('completed', '已完成'),
        ('blocked', '已阻断'), ('failed', '失败'), ('cancelled', '已取消'), ('timed_out', '已超时'),
    )
    job_id = models.CharField('任务ID', max_length=64, unique=True, db_index=True)
    job_type = models.CharField('任务类型', max_length=40, db_index=True)
    status = models.CharField('任务状态', max_length=20, choices=STATUS_CHOICES, default='queued', db_index=True)
    payload = models.JSONField('任务参数', default=dict)
    result_ref = models.CharField('结果引用', max_length=160, blank=True)
    request_id = models.CharField('请求ID', max_length=64, blank=True, db_index=True)
    caller_id = models.CharField('调用方', max_length=160, blank=True, db_index=True)
    tool_name = models.CharField('工具名称', max_length=100, blank=True, db_index=True)
    idempotency_fingerprint = models.CharField('幂等指纹', max_length=64, null=True, blank=True, unique=True)
    current_stage = models.CharField('当前阶段', max_length=40, blank=True)
    progress = models.JSONField('任务进度', default=dict, blank=True)
    error_code = models.CharField('错误码', max_length=64, blank=True)
    error = models.TextField('错误信息', blank=True)
    attempts = models.PositiveSmallIntegerField('尝试次数', default=0)
    max_attempts = models.PositiveSmallIntegerField('最大尝试次数', default=3)
    locked_by = models.CharField('执行节点', max_length=120, blank=True)
    locked_at = models.DateTimeField('锁定时间', null=True, blank=True)
    available_at = models.DateTimeField('可执行时间', auto_now_add=True, db_index=True)
    started_at = models.DateTimeField('开始时间', null=True, blank=True)
    finished_at = models.DateTimeField('结束时间', null=True, blank=True)
    cancel_requested_at = models.DateTimeField('取消请求时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'runtime_jobs'
        ordering = ('created_at',)
        indexes = [models.Index(fields=('status', 'available_at'), name='runtime_job_ready_idx')]


class PipelineRunRecord(models.Model):
    """Database index for pipeline state; large artifacts stay on durable storage."""

    run_id = models.CharField('运行ID', max_length=64, unique=True, db_index=True)
    status = models.CharField('运行状态', max_length=24, db_index=True)
    current_stage = models.CharField('当前阶段', max_length=40, blank=True)
    scenario_id = models.CharField('场景ID', max_length=80, blank=True, db_index=True)
    original_name = models.CharField('源文件名', max_length=255, blank=True)
    snapshot = models.JSONField('运行快照', default=dict)
    artifact_manifest = models.JSONField('产物清单', default=dict)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'pipeline_run_records'
        ordering = ('-created_at',)


class SkillRunRecord(models.Model):
    skill_run_id = models.CharField('Skill运行ID', max_length=64, unique=True, db_index=True)
    pipeline_run_id = models.CharField('流水线运行ID', max_length=64, blank=True, db_index=True)
    status = models.CharField('运行状态', max_length=24, default='running', db_index=True)
    last_sequence = models.PositiveIntegerField('最后事件序号', default=0)
    event_count = models.PositiveIntegerField('事件数量', default=0)
    payload_bytes = models.PositiveBigIntegerField('事件载荷字节数', default=0)
    result = models.JSONField('运行结果', null=True, blank=True)
    error = models.TextField('错误信息', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'skill_run_records'
        ordering = ('-created_at',)


class SkillRunEvent(models.Model):
    run = models.ForeignKey(SkillRunRecord, related_name='events', on_delete=models.CASCADE)
    sequence = models.PositiveIntegerField('事件序号')
    event_type = models.CharField('事件类型', max_length=64)
    stage = models.CharField('阶段', max_length=64)
    status = models.CharField('状态', max_length=32)
    message = models.TextField('消息', blank=True)
    payload = models.JSONField('完整事件', default=dict)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'skill_run_events'
        ordering = ('sequence',)
        constraints = [models.UniqueConstraint(fields=('run', 'sequence'), name='unique_skill_run_sequence')]


class ControlApproval(models.Model):
    """Human approval record. It never sends commands to plant equipment."""

    STATUS_CHOICES = (('pending', '待审批'), ('approved', '已批准'), ('rejected', '已拒绝'), ('expired', '已过期'))
    approval_id = models.CharField('审批ID', max_length=64, unique=True, db_index=True)
    study = models.ForeignKey(OptimizationStudy, related_name='control_approvals', on_delete=models.CASCADE)
    candidate_run = models.ForeignKey(OptimizationRun, related_name='+', on_delete=models.PROTECT)
    status = models.CharField('审批状态', max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    safety_assessment = models.JSONField('安全评估', default=dict)
    requested_by = models.CharField('申请人', max_length=150, blank=True)
    reviewed_by = models.CharField('审批人', max_length=150, blank=True)
    review_comment = models.TextField('审批意见', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    reviewed_at = models.DateTimeField('审批时间', null=True, blank=True)

    class Meta:
        db_table = 'control_approvals'
        ordering = ('-created_at',)


class KnowledgeDocument(models.Model):
    STATUS_CHOICES = (('draft', '草稿'), ('approved', '已审核'), ('retired', '已停用'))
    document_id = models.CharField('文档标识', max_length=120, unique=True, db_index=True)
    title = models.CharField('标题', max_length=255)
    source_type = models.CharField('来源类型', max_length=40, default='builtin')
    source_uri = models.CharField('来源地址', max_length=500, blank=True)
    scene_id = models.CharField('场景ID', max_length=80, blank=True, db_index=True)
    version = models.CharField('版本', max_length=40, default='1.0')
    status = models.CharField('审核状态', max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    checksum = models.CharField('内容校验值', max_length=64, blank=True)
    approved_by = models.CharField('审核人', max_length=150, blank=True)
    effective_at = models.DateTimeField('生效时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'knowledge_documents'
        ordering = ('scene_id', 'title')

    def __str__(self):
        return self.title


class KnowledgeChunk(models.Model):
    document = models.ForeignKey(KnowledgeDocument, related_name='chunks', on_delete=models.CASCADE)
    chunk_id = models.CharField('知识片段标识', max_length=160, unique=True, db_index=True)
    ordinal = models.PositiveIntegerField('片段序号', default=1)
    content = models.TextField('知识内容')
    keywords = models.JSONField('关键词', default=list)
    metadata = models.JSONField('元数据', default=dict)
    embedding_ref = models.CharField('向量引用', max_length=255, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'knowledge_chunks'
        ordering = ('document_id', 'ordinal')
        constraints = [models.UniqueConstraint(fields=('document', 'ordinal'), name='unique_knowledge_doc_chunk')]


class KnowledgeEntity(models.Model):
    STATUS_CHOICES = KnowledgeDocument.STATUS_CHOICES
    entity_id = models.CharField('实体标识', max_length=160, unique=True, db_index=True)
    entity_type = models.CharField('实体类型', max_length=40, db_index=True)
    canonical_name = models.CharField('标准名称', max_length=255)
    scene_id = models.CharField('场景ID', max_length=80, blank=True, db_index=True)
    attributes = models.JSONField('属性', default=dict)
    status = models.CharField('审核状态', max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    source_document = models.ForeignKey(KnowledgeDocument, null=True, blank=True, related_name='entities', on_delete=models.SET_NULL)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'knowledge_entities'
        ordering = ('entity_type', 'canonical_name')

    def __str__(self):
        return self.canonical_name


class KnowledgeAlias(models.Model):
    entity = models.ForeignKey(KnowledgeEntity, related_name='aliases', on_delete=models.CASCADE)
    alias = models.CharField('别名', max_length=255)
    normalized_alias = models.CharField('归一化别名', max_length=255, db_index=True)
    language = models.CharField('语言', max_length=20, default='zh-CN')
    priority = models.PositiveSmallIntegerField('优先级', default=50)

    class Meta:
        db_table = 'knowledge_aliases'
        ordering = ('-priority', 'alias')
        constraints = [models.UniqueConstraint(fields=('entity', 'normalized_alias'), name='unique_entity_alias')]


class KnowledgeRelation(models.Model):
    STATUS_CHOICES = KnowledgeDocument.STATUS_CHOICES
    relation_id = models.CharField('关系标识', max_length=180, unique=True, db_index=True)
    subject = models.ForeignKey(KnowledgeEntity, related_name='outgoing_relations', on_delete=models.CASCADE)
    predicate = models.CharField('关系类型', max_length=80, db_index=True)
    object_entity = models.ForeignKey(KnowledgeEntity, null=True, blank=True, related_name='incoming_relations', on_delete=models.CASCADE)
    object_value = models.CharField('关系值', max_length=500, blank=True)
    confidence = models.DecimalField('置信度', max_digits=4, decimal_places=3, default=Decimal('1.0'))
    status = models.CharField('审核状态', max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    source_document = models.ForeignKey(KnowledgeDocument, null=True, blank=True, related_name='relations', on_delete=models.SET_NULL)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'knowledge_relations'


class SkillKnowledgeRule(models.Model):
    STATUS_CHOICES = KnowledgeDocument.STATUS_CHOICES
    rule_id = models.CharField('规则标识', max_length=180, unique=True, db_index=True)
    skill_id = models.CharField('Skill ID', max_length=120, db_index=True)
    scene_id = models.CharField('场景ID', max_length=80, blank=True, db_index=True)
    intent_patterns = models.JSONField('意图表达', default=list)
    positive_terms = models.JSONField('正向术语', default=list)
    negative_terms = models.JSONField('排除术语', default=list)
    requires_artifacts = models.JSONField('前置产物', default=list)
    priority = models.PositiveSmallIntegerField('优先级', default=50)
    confidence = models.DecimalField('基础置信度', max_digits=4, decimal_places=3, default=Decimal('0.84'))
    status = models.CharField('审核状态', max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    rationale = models.TextField('规则依据', blank=True)
    source_document = models.ForeignKey(KnowledgeDocument, null=True, blank=True, related_name='skill_rules', on_delete=models.SET_NULL)
    version = models.CharField('版本', max_length=40, default='1.0')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'skill_knowledge_rules'
        ordering = ('-priority', 'skill_id')


class RoutingFeedback(models.Model):
    OUTCOME_CHOICES = (('accepted', '命中正确'), ('corrected', '已纠正'), ('rejected', '错误召回'))
    query = models.TextField('用户问题')
    scene_id = models.CharField('场景ID', max_length=80, blank=True, db_index=True)
    retrieval_context = models.JSONField('检索上下文', default=dict)
    predicted_skill_ids = models.JSONField('预测 Skill', default=list)
    corrected_skill_ids = models.JSONField('纠正 Skill', default=list)
    outcome = models.CharField('反馈结果', max_length=20, choices=OUTCOME_CHOICES, db_index=True)
    reviewed_by = models.CharField('复核人', max_length=150, blank=True)
    note = models.TextField('备注', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    reviewed_at = models.DateTimeField('复核时间', null=True, blank=True)

    class Meta:
        db_table = 'routing_feedback'
        ordering = ('-created_at',)


class FileAsset(models.Model):
    """A14-owned immutable source file; archive preserves reproduction copies."""
    asset_id = models.CharField(max_length=64, primary_key=True)
    owner_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    project = models.CharField(max_length=32, default='A14')
    display_name = models.CharField(max_length=255)
    storage_ref = models.CharField(max_length=255)
    source_type = models.CharField(max_length=32, default='upload')
    content_hash = models.CharField(max_length=64, db_index=True)
    size = models.PositiveBigIntegerField()
    rows = models.PositiveIntegerField(null=True)
    columns = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=32, default='active')
    related_runs = models.JSONField(default=list)

    class Meta:
        ordering = ['-created_at']
