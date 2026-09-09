from django.contrib import admin

from .models import (
    AgentReview,
    CleaningRecord,
    CollinearityResult,
    DataFile,
    DynamicSegment,
    ExportRecord,
    LagAnalysisResult,
    ModelResult,
    OptimizationRun,
    OptimizationStudy,
    ScenarioTemplate,
    StandardCheck,
    VariableMapping,
)


admin.site.site_header = '流程工业 APC 建模数据优选 Agent 工作台'
admin.site.site_title = 'APC Agent 后台'
admin.site.index_title = 'APC建模数据优选'


@admin.register(ScenarioTemplate)
class ScenarioTemplateAdmin(admin.ModelAdmin):
    list_display = (
        'scenario_name',
        'industry_type',
        'input_variables',
        'output_variables',
        'modeling_objective',
        'evaluation_metrics',
        'created_at',
    )
    search_fields = ('scenario_name', 'industry_type', 'input_variables', 'output_variables', 'modeling_objective')
    list_filter = ('industry_type', 'created_at')
    ordering = ('scenario_name',)


@admin.register(DataFile)
class DataFileAdmin(admin.ModelAdmin):
    list_display = (
        'file_name',
        'scenario',
        'uploaded_at',
        'row_count',
        'variable_count',
        'sampling_period',
        'missing_value_ratio',
        'outlier_ratio',
        'processing_status',
    )
    search_fields = ('file_name', 'scenario__scenario_name', 'file_path', 'processing_status')
    list_filter = ('scenario', 'processing_status', 'uploaded_at')
    autocomplete_fields = ('scenario',)
    ordering = ('-uploaded_at',)


@admin.register(VariableMapping)
class VariableMappingAdmin(admin.ModelAdmin):
    list_display = (
        'original_field_name',
        'standard_variable_name',
        'scenario',
        'variable_role',
        'variable_unit',
        'lower_limit',
        'upper_limit',
        'is_required',
    )
    search_fields = ('original_field_name', 'standard_variable_name', 'scenario__scenario_name', 'variable_role')
    list_filter = ('scenario', 'variable_role', 'is_required')
    autocomplete_fields = ('scenario',)
    ordering = ('scenario__scenario_name', 'variable_role', 'standard_variable_name')


@admin.register(StandardCheck)
class StandardCheckAdmin(admin.ModelAdmin):
    list_display = (
        'file',
        'check_item',
        'check_result',
        'problem_description',
        'repair_suggestion',
        'checked_at',
    )
    search_fields = ('file__file_name', 'check_item', 'check_result', 'problem_description', 'repair_suggestion')
    list_filter = ('check_result', 'checked_at')
    autocomplete_fields = ('file',)
    ordering = ('-checked_at',)


@admin.register(CleaningRecord)
class CleaningRecordAdmin(admin.ModelAdmin):
    list_display = (
        'file',
        'missing_value_method',
        'outlier_threshold',
        'resampling_period',
        'before_cleaning_count',
        'after_cleaning_count',
        'missing_value_ratio',
        'outlier_ratio',
        'cleaning_status',
        'cleaned_at',
    )
    search_fields = ('file__file_name', 'missing_value_method', 'outlier_threshold', 'cleaning_status')
    list_filter = ('cleaning_status', 'cleaned_at')
    autocomplete_fields = ('file',)
    ordering = ('-cleaned_at',)


@admin.register(DynamicSegment)
class DynamicSegmentAdmin(admin.ModelAdmin):
    list_display = (
        'file',
        'start_time',
        'end_time',
        'dynamic_score',
        'snr_score',
        'integrity_score',
        'abnormal_ratio',
        'overall_score',
        'selected_for_modeling',
    )
    search_fields = ('file__file_name',)
    list_filter = ('selected_for_modeling', 'start_time', 'end_time')
    autocomplete_fields = ('file',)
    ordering = ('-overall_score', '-start_time')


@admin.register(LagAnalysisResult)
class LagAnalysisResultAdmin(admin.ModelAdmin):
    list_display = (
        'file',
        'input_variable',
        'output_variable',
        'optimal_lag',
        'correlation_score',
        'compensation_method',
        'analyzed_at',
    )
    search_fields = ('file__file_name', 'input_variable', 'output_variable', 'compensation_method')
    list_filter = ('compensation_method', 'analyzed_at')
    autocomplete_fields = ('file',)
    ordering = ('-analyzed_at',)


@admin.register(CollinearityResult)
class CollinearityResultAdmin(admin.ModelAdmin):
    list_display = (
        'file',
        'variable_a',
        'variable_b',
        'correlation_coefficient',
        'collinearity_level',
        'processing_method',
        'is_retained',
        'analyzed_at',
    )
    search_fields = ('file__file_name', 'variable_a', 'variable_b', 'collinearity_level', 'processing_method')
    list_filter = ('collinearity_level', 'is_retained', 'analyzed_at')
    autocomplete_fields = ('file',)
    ordering = ('-analyzed_at', '-correlation_coefficient')


@admin.register(ModelResult)
class ModelResultAdmin(admin.ModelAdmin):
    list_display = (
        'file',
        'model_type',
        'training_data_source',
        'r2',
        'rmse',
        'mae',
        'fitting_degree',
        'model_file_path',
        'trained_at',
    )
    search_fields = ('file__file_name', 'model_type', 'training_data_source', 'model_file_path')
    list_filter = ('model_type', 'training_data_source', 'trained_at')
    autocomplete_fields = ('file',)
    ordering = ('-trained_at', '-fitting_degree')


@admin.register(OptimizationRun)
class OptimizationRunAdmin(admin.ModelAdmin):
    list_display = (
        'study',
        'file',
        'round_number',
        'dynamic_segment_threshold',
        'outlier_threshold',
        'collinearity_threshold',
        'lag_search_range',
        'model_r2',
        'model_fit',
        'rmse',
        'coverage_ratio',
        'overall_score',
        'is_best',
        'review_result',
        'created_at',
    )
    search_fields = ('study__project_code', 'file__file_name', 'outlier_threshold', 'lag_search_range', 'review_result')
    list_filter = ('is_best', 'review_result', 'created_at')
    autocomplete_fields = ('file',)
    ordering = ('-created_at', '-overall_score')


@admin.register(OptimizationStudy)
class OptimizationStudyAdmin(admin.ModelAdmin):
    list_display = (
        'project_code',
        'project_name',
        'dataset_mode',
        'status',
        'run_mode',
        'current_round',
        'total_rounds',
        'no_improvement_rounds',
        'early_stopped',
        'best_run',
        'created_at',
        'finished_at',
    )
    search_fields = ('project_code', 'project_name')
    list_filter = ('dataset_mode', 'run_mode', 'status', 'early_stopped', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'started_at', 'finished_at', 'accepted_at')
    ordering = ('-created_at',)


@admin.register(AgentReview)
class AgentReviewAdmin(admin.ModelAdmin):
    list_display = (
        'file',
        'execution_agent_output',
        'review_agent_conclusion',
        'data_quality_result',
        'dynamic_segment_validity_result',
        'lag_compensation_result',
        'collinearity_processing_result',
        'model_fitting_result',
        'modification_suggestions',
        'is_passed',
        'reviewed_at',
    )
    search_fields = (
        'file__file_name',
        'execution_agent_output',
        'review_agent_conclusion',
        'modification_suggestions',
    )
    list_filter = ('is_passed', 'data_quality_result', 'reviewed_at')
    autocomplete_fields = ('file',)
    ordering = ('-reviewed_at',)


@admin.register(ExportRecord)
class ExportRecordAdmin(admin.ModelAdmin):
    list_display = (
        'file',
        'export_type',
        'export_file_name',
        'export_path',
        'exported_at',
        'export_status',
    )
    search_fields = ('file__file_name', 'export_type', 'export_file_name', 'export_path', 'export_status')
    list_filter = ('export_type', 'export_status', 'exported_at')
    autocomplete_fields = ('file',)
    ordering = ('-exported_at',)
