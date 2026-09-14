from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from .models import KnowledgeChunk, KnowledgeDocument, KnowledgeEntity, RoutingFeedback, SkillKnowledgeRule
from .services.knowledge_base import search_knowledge
from .services.scene_registry import list_scene_configs
from .skills.catalog import SKILL_MAP


@require_GET
def knowledge_summary(request):
    scenes = [row for row in list_scene_configs() if row.get('official')]
    approved_rules = SkillKnowledgeRule.objects.filter(status='approved')
    covered = set(approved_rules.values_list('skill_id', flat=True))
    return JsonResponse({'ok': True, 'data': {
        'documents': {'total': KnowledgeDocument.objects.count(),
                      'approved': KnowledgeDocument.objects.filter(status='approved').count(),
                      'draft': KnowledgeDocument.objects.filter(status='draft').count()},
        'chunks': KnowledgeChunk.objects.filter(document__status='approved').count(),
        'entities': KnowledgeEntity.objects.filter(status='approved').count(),
        'scene_coverage': [{'id': row['id'], 'name': row['name'],
                            'entity_count': KnowledgeEntity.objects.filter(status='approved', scene_id=row['id']).count()}
                           for row in scenes],
        'skill_coverage': {'covered': len(covered & set(SKILL_MAP)), 'total': len(SKILL_MAP),
                           'missing': sorted(set(SKILL_MAP) - covered)},
        'feedback': {'total': RoutingFeedback.objects.count(),
                     'corrected': RoutingFeedback.objects.filter(outcome='corrected').count()},
        'retrieval_mode': 'structured_lexical_v1',
        'vector_index': 'reserved',
    }}, json_dumps_params={'ensure_ascii': False})


@require_GET
def knowledge_search(request):
    query = str(request.GET.get('q', '')).strip()
    if not query:
        return JsonResponse({'ok': False, 'message': '缺少检索参数 q'}, status=400)
    scene_id = str(request.GET.get('scene_id', '')).strip()
    try:
        limit = min(max(int(request.GET.get('limit', 8)), 1), 20)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'message': 'limit 必须是整数'}, status=400)
    return JsonResponse({'ok': True, 'data': search_knowledge(query, scene_id, limit)},
                        json_dumps_params={'ensure_ascii': False})


@require_http_methods(['POST'])
def knowledge_feedback(request):
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'message': '请求体不是合法 JSON'}, status=400)
    query = str(payload.get('query', '')).strip()
    outcome = payload.get('outcome')
    predicted = payload.get('predicted_skill_ids', [])
    corrected = payload.get('corrected_skill_ids', [])
    if not query or outcome not in {'accepted', 'corrected', 'rejected'}:
        return JsonResponse({'ok': False, 'message': 'query 与合法 outcome 为必填项'}, status=400)
    if not isinstance(predicted, list) or not isinstance(corrected, list):
        return JsonResponse({'ok': False, 'message': 'Skill ID 必须使用数组'}, status=400)
    unknown = (set(map(str, predicted)) | set(map(str, corrected))) - set(SKILL_MAP)
    if unknown:
        return JsonResponse({'ok': False, 'message': f"未知 Skill：{', '.join(sorted(unknown))}"}, status=400)
    record = RoutingFeedback.objects.create(
        query=query, scene_id=str(payload.get('scene_id', '')),
        retrieval_context=payload.get('retrieval_context', {}),
        predicted_skill_ids=predicted, corrected_skill_ids=corrected, outcome=outcome,
        reviewed_by=str(payload.get('reviewed_by', '')), note=str(payload.get('note', '')),
    )
    return JsonResponse({'ok': True, 'data': {'id': record.id, 'outcome': record.outcome}}, status=201)
