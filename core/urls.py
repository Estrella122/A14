from django.urls import path

from . import agent_api, api, integration_api, optimization_api, pipeline_api


urlpatterns = [
    path('', api.api_index, name='api-index'),
    path('security/session/', api.security_session, name='security-session'),
    path('integration/', integration_api.integration_summary, name='integration-summary'),
    path('integration/<slug:module_key>/', integration_api.integration_module, name='integration-module'),
    path('agent/chat/', agent_api.agent_chat, name='agent-chat'),
    path('agent/skills/', agent_api.agent_skills, name='agent-skills'),
    path('agent/plans/', agent_api.agent_plan, name='agent-plan'),
    path('agent/skill-runs/', agent_api.agent_skill_run_collection, name='agent-skill-run-collection'),
    path('agent/skill-runs/<slug:skill_run_id>/', agent_api.agent_skill_run_detail, name='agent-skill-run-detail'),
    path('agent/skill-runs/<slug:skill_run_id>/events/', agent_api.agent_skill_run_events, name='agent-skill-run-events'),
    path('agent/runs/<slug:run_id>/trace/', agent_api.agent_trace, name='agent-trace'),
    path('pipeline/runs/', pipeline_api.pipeline_collection, name='pipeline-run-collection'),
    path('pipeline/runs/latest/', pipeline_api.pipeline_latest, name='pipeline-run-latest'),
    path('pipeline/runs/<slug:run_id>/', pipeline_api.pipeline_detail, name='pipeline-run-detail'),
    path('pipeline/runs/<slug:run_id>/rerun/', pipeline_api.pipeline_rerun, name='pipeline-run-rerun'),
    path('pipeline/runs/<slug:run_id>/artifacts/<slug:artifact_key>/', pipeline_api.pipeline_artifact, name='pipeline-run-artifact'),
    path('pipeline/workflows/execute/', pipeline_api.pipeline_workflow_execute, name='pipeline-workflow-execute'),
    path('optimization/studies/', optimization_api.study_collection, name='optimization-study-collection'),
    path('optimization/studies/<int:study_id>/', optimization_api.study_detail, name='optimization-study-detail'),
    path('optimization/studies/<int:study_id>/step/', optimization_api.study_step, name='optimization-study-step'),
    path('optimization/studies/<int:study_id>/accept/', optimization_api.study_accept, name='optimization-study-accept'),
    path('optimization/studies/<int:study_id>/export/', optimization_api.study_export, name='optimization-study-export'),
    path('<slug:table_key>/', api.table_collection, name='api-table-collection'),
]
