from __future__ import annotations

import re
from typing import Any

from django.db import DatabaseError
from django.test.testcases import DatabaseOperationForbidden

from core.models import KnowledgeChunk, KnowledgeEntity, SkillKnowledgeRule
from django.db.models import Q


GENERIC_TERMS = frozenset({'分析', '数据', '处理', '结果', '检查', '当前', '问题', '模型', '执行', '生成'})


def normalize_text(value: str) -> str:
    return re.sub(r'\s+', '', str(value or '').strip().lower())


def _term_hits(query: str, terms: list[str]) -> list[str]:
    return [term for term in terms if normalize_text(term) and normalize_text(term) in query]


def search_knowledge(query: str, scene_id: str = '', limit: int = 8) -> dict[str, Any]:
    """Deterministic, auditable retrieval. Only approved knowledge is visible."""
    normalized = normalize_text(re.sub(r'(?:不要|无需|不必|别)(?:讨论|回答|提及|涉及|分析)[^，。；,;]*', '', query))
    empty = {
        'query': query, 'scene_id': scene_id, 'retrieval_mode': 'structured_lexical_v2',
        'skill_suggestions': [], 'entities': [], 'documents': [], 'provenance': [],
    }
    if not normalized:
        return empty
    try:
        suggestions: list[dict[str, Any]] = []
        rules = SkillKnowledgeRule.objects.filter(status='approved').filter(Q(source_document__isnull=True) | Q(source_document__status='approved')).select_related('source_document')
        if scene_id:
            rules = rules.filter(scene_id__in=('', scene_id))
        for rule in rules:
            positives = [str(term) for term in (rule.positive_terms or [])]
            patterns = [str(term) for term in (rule.intent_patterns or [])]
            negative_hits = _term_hits(normalized, [str(term) for term in (rule.negative_terms or [])])
            hits = _term_hits(normalized, positives + patterns)
            specific_hits = [hit for hit in hits if normalize_text(hit) not in GENERIC_TERMS]
            if negative_hits or not specific_hits:
                continue
            score = min(float(rule.confidence) + 0.025 * (len(set(specific_hits)) - 1), 0.98)
            if rule.scene_id and rule.scene_id == scene_id:
                score = min(score + 0.02, 0.99)
            suggestions.append({
                'skill_id': rule.skill_id, 'score': round(score, 3),
                'matched_terms': sorted(set(specific_hits), key=lambda item: (-len(item), item)),
                'rule_id': rule.rule_id, 'rationale': rule.rationale,
                'requires_artifacts': rule.requires_artifacts,
                'source_document_id': rule.source_document.document_id if rule.source_document else None,
            })
        suggestions.sort(key=lambda row: (-row['score'], row['skill_id']))

        entities = []
        entity_query = KnowledgeEntity.objects.filter(status='approved').prefetch_related('aliases')
        if scene_id:
            entity_query = entity_query.filter(scene_id__in=('', scene_id))
        for entity in entity_query:
            names = [entity.canonical_name, *(alias.alias for alias in entity.aliases.all())]
            matches = [name for name in names if normalize_text(name) in normalized]
            if matches:
                entities.append({
                    'entity_id': entity.entity_id, 'entity_type': entity.entity_type,
                    'name': entity.canonical_name, 'scene_id': entity.scene_id,
                    'matched_alias': max(matches, key=len), 'attributes': entity.attributes,
                })

        documents = []
        chunks = KnowledgeChunk.objects.filter(document__status='approved').select_related('document')
        if scene_id:
            chunks = chunks.filter(document__scene_id__in=('', scene_id))
        approved_count = chunks.count()
        body_terms = set(re.findall(r'[a-z][a-z0-9_]+', normalized))
        for phrase in re.findall(r'[\u4e00-\u9fff]+', normalized):
            for size in (2, 3, 4):
                body_terms.update(phrase[i:i+size] for i in range(len(phrase)-size+1))
        body_terms -= GENERIC_TERMS | {'是什么', '为什么', '怎么', '如何', '多少', '哪些', '这份', '当前数据', '本次', '告诉', '告诉我'}
        for chunk in chunks:
            # Existing schema has global/scene knowledge; optional project ACL in
            # metadata is restrictive. Never expose a scoped chunk without scope.
            if (chunk.metadata or {}).get('project_id') or (chunk.metadata or {}).get('allowed_users'):
                continue
            hits = _term_hits(normalized, [str(term) for term in (chunk.keywords or [])])
            aliases = [row['name'] for row in entities]
            recall_terms = body_terms | {normalize_text(term) for term in hits + aliases}
            paragraphs = [part.strip() for part in re.split(r'\n+|(?<=[。！？])', chunk.content) if part.strip()]
            ranked = []
            for i, paragraph in enumerate(paragraphs):
                text = normalize_text(paragraph)
                terms = [term for term in recall_terms if term and term in text]
                score = sum(min(len(term), 6) for term in terms) + 8 * sum(normalize_text(term) in text for term in hits)
                ranked.append((score, -i, terms))
            best = max(ranked, default=(0, 0, []))
            if not hits and best[0] < 4:
                continue
            index = -best[1]
            excerpt = ''.join(paragraphs[index:index+3])[:900]
            if not excerpt:
                continue
            documents.append({
                'document_id': chunk.document.document_id, 'title': chunk.document.title,
                'chunk_id': chunk.chunk_id, 'scene_id': chunk.document.scene_id,
                'version': chunk.document.version or None,
                'source_locator': (chunk.metadata or {}).get('source_locator'),
                'retrieval_score': best[0] + len(hits)*10,
                'matched_terms': sorted(set(hits + best[2]), key=lambda item: (-len(item), item)),
                'relevant_excerpt': excerpt, 'excerpt': excerpt,
                'excerpt_truncated': len(''.join(paragraphs[index:index+3])) > 900,
                'source_type': chunk.document.source_type, 'source_uri': chunk.document.source_uri,
                'category': (chunk.metadata or {}).get('category') or ('scene_knowledge' if chunk.document.scene_id else 'algorithm_knowledge'),
            })
        documents.sort(key=lambda row: (-row['retrieval_score'], row['document_id'], row['chunk_id']))
        candidate_count = len(documents)
        documents = documents[:limit]
        provenance = sorted({row['source_document_id'] for row in suggestions if row['source_document_id']} | {row['document_id'] for row in documents})
        return {**empty, 'skill_suggestions': suggestions[:limit], 'entities': entities[:limit],
                'documents': documents, 'provenance': provenance,
                'observability': {'status': 'matched' if documents else 'no_relevant_match' if approved_count else 'content_absent',
                                  'approved_chunk_count': approved_count, 'candidate_count': candidate_count,
                                  'returned_count': len(documents), 'truncated': candidate_count > limit or any(d['excerpt_truncated'] for d in documents)}}
    except (DatabaseError, DatabaseOperationForbidden):
        # During first deployment or isolated unit tests the migration/seed may not
        # exist yet. The existing deterministic router remains fully functional.
        return {**empty, 'unavailable': True, 'observability': {'status': 'retrieval_unavailable', 'error_reason': 'database_not_ready_or_access_unavailable'}}


def routing_skill_ids(query: str, scene_id: str = '', threshold: float = 0.84) -> tuple[set[str], dict[str, float], dict[str, Any]]:
    result = search_knowledge(query, scene_id=scene_id)
    selected = {row['skill_id'] for row in result['skill_suggestions'] if row['score'] >= threshold}
    scores = {row['skill_id']: row['score'] for row in result['skill_suggestions'] if row['skill_id'] in selected}
    return selected, scores, result
