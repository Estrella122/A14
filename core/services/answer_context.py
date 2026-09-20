"""One bounded evidence context for deterministic and LLM answers."""
import json
import re
from copy import deepcopy
from .knowledge_base import search_knowledge
from .task_admission import capability_availability


def build_answer_context(message, snapshot, response, budget=24000):
    from .evidence_values import final_result_view
    snapshot = final_result_view(snapshot)
    results = snapshot.get('results', {})
    standard = results.get('standardization', {})
    scene = standard.get('scenario', {})
    retrieval = search_knowledge(message, scene.get('scenario_id', ''))
    def pick(source, names):
        return {k: deepcopy(source[k]) for k in names if k in source}
    run = {
        'run_id': snapshot.get('run_id'), 'status': snapshot.get('status'),
        'current_stage': snapshot.get('current_stage'), 'error': snapshot.get('error'), 'stop_reason': snapshot.get('stop_reason'),
        'standardization': {'scenario': pick(scene, ('scenario_id', 'scenario_name', 'primary_output')),
                            'mapping': pick(standard.get('mapping', {}), ('missing_required', 'review_count', 'required_coverage')),
                            'data_decision': standard.get('data_decision', {})},
        'cleaning': pick(results.get('cleaning', {}), ('missing_rate', 'logs', 'snr', 'split', 'selection_metrics', 'selected_segment_count', 'strict_selected_segment_count', 'usable_segment_count', 'modeling_row_count', 'selection_acceptance_mode')),
        'modeling': pick(results.get('modeling', {}), ('status', 'config', 'metrics', 'fitted_inputs', 'fitted_state', 'diagnostics', 'collinearity')),
        'optimization': pick(results.get('optimization', {}), ('best_parameters', 'best_metrics', 'stopping', 'iterations', 'candidate_counts', 'execution_status', 'optimization_outcome', 'stop_reason')),
        'policy_receipt': snapshot.get('policy_receipt', {}),
    }
    if response.get('basic_data_profile'):
        run['basic_data_profile'] = response['basic_data_profile']
    # Only current invocation outputs; never pull a latest/unrelated Skill run.
    current = []
    for row in response.get('runtime_observability', {}).get('executor_results', []):
        current.append(pick(row, ('skill_id', 'status', 'metrics', 'evidence', 'artifacts')))
    run['skill_results'] = current
    plan = response.get('skill_plan', {})
    skills = [{'skill_id': row.get('skill_id'), 'name': row.get('name'), 'mode': plan.get('mode')}
              for row in plan.get('steps', [])][:16]
    from core.skills.registry import get_registry
    registry = get_registry()
    if not skills:
        skills = [{'skill_id': row.get('skill_id') or row.get('id')} for row in registry.search(message)[:3]]
    for item in skills:
        manifest = registry.get(item.get('skill_id'))
        if manifest:
            item.update(capability=getattr(manifest, 'description', getattr(manifest, 'metadata', {}).get('description')), requires=list(getattr(manifest, 'requires', ())),
                        execution_mode=getattr(manifest, 'execution_mode', None), method_document=registry.get_prompt_content(item['skill_id'])[:1400],
                        source_uri=str(manifest.path) if getattr(manifest, 'path', None) else None, version=getattr(manifest, 'version', None))
    context = {'run_evidence': run, 'knowledge_context': [], 'skill_context': skills,
               'capability_availability': response.get('capability_availability') or capability_availability(snapshot),
               'retrieval_observability': retrieval.get('observability', {}),
               'missing_evidence': [], 'context_observability': {'budget_characters': budget, 'truncated_fields': []}}
    if not snapshot.get('run_id'):
        context['missing_evidence'].append('current_run')
    if not retrieval.get('documents'):
        context['missing_evidence'].append('citable_knowledge')
    # Bound high-volume run evidence first; retain metrics and provenance.
    for section, key, cap in (('cleaning', 'logs', 12), ('optimization', 'iterations', 8), ('modeling', 'collinearity', 1)):
        value = run[section].get(key)
        if isinstance(value, list) and len(value) > cap:
            run[section][key] = value[:cap]
            context['context_observability']['truncated_fields'].append(f'{section}.{key}')
        if isinstance(value, dict) and len(json.dumps(value, default=str)) > 4000:
            run[section][key] = {'omitted': 'see current run artifact'}
            context['context_observability']['truncated_fields'].append(f'{section}.{key}')
    def bound(value, path='run_evidence'):
        if isinstance(value, str) and len(value) > 1600:
            context['context_observability']['truncated_fields'].append(path)
            return value[:1600]
        if isinstance(value, list):
            if len(value) > 20:
                context['context_observability']['truncated_fields'].append(path)
            return [bound(item, path) for item in value[:20]]
        if isinstance(value, dict):
            return {k: bound(v, f'{path}.{k}') for k, v in value.items() if k.lower() not in {'api_key', 'credential', 'authorization', 'password'}}
        return value
    context['run_evidence'] = bound(run)
    # Reserve current-run facts before any optional matrices, logs or knowledge.
    model = run['modeling']
    optimization = results.get('optimization', {})
    core = {
        'run_id': snapshot.get('run_id'), 'status': snapshot.get('status'),
        'current_stage': snapshot.get('current_stage'), 'error': snapshot.get('error'), 'stop_reason': snapshot.get('stop_reason'),
        'source': {'original_name': snapshot.get('original_name'), 'scenario': run['standardization']},
        'modeling': pick(model, ('status', 'config', 'metrics', 'fitted_inputs', 'diagnostics')),
        'optimization': pick(optimization, ('best_round', 'best_parameters', 'best_metrics', 'best_score', 'best_feasible', 'selection_warnings', 'selection_rule', 'stopping', 'candidate_counts', 'execution_status', 'optimization_outcome', 'stop_reason')),
        'selection': results.get('best_selection_receipt') or pick(run['cleaning'], ('selection_metrics', 'modeling_row_count', 'strict_selected_segment_count', 'usable_segment_count')),
        'policy_receipt': {'scope': 'initial_baseline_policy; winner overrides are recorded separately', **snapshot.get('policy_receipt', {})},
        'winner_effective_policy': results.get('best_selection_receipt', {}).get('effective_policy', {'status': 'historical_not_recorded', 'recorded_winner_parameters': results.get('best_selection_receipt', {}).get('requested_parameters', {})}),
        'artifacts': snapshot.get('artifacts', {}),
        'missing_evidence': [name for name in ('modeling', 'optimization', 'cleaning') if not results.get(name)],
    }
    # Large per-row identifiers and fitted coefficients are available by artifact.
    core['selection'] = {k: v for k, v in core['selection'].items() if k not in {'selected_row_ids', 'selected_window_ids', 'selected_windows'}}
    core['modeling']['diagnostics'] = pick(model.get('diagnostics', {}), ('train', 'validation', 'test', 'baseline', 'baselines', 'warnings', 'test_evaluation_count'))
    core = bound(core, 'core_facts')
    context['core_facts'] = core
    context['context_observability']['retained_core_fields'] = list(core)
    size = lambda value: len(json.dumps(value, ensure_ascii=False, default=str))
    if size({'core_facts': core}) + 1000 > budget:
        # Callers must use deterministic evidence when even the core will not fit.
        context = {'core_facts': core, 'run_evidence': {}, 'knowledge_context': [], 'skill_context': [],
                   'capability_availability': context['capability_availability'],
                   'missing_evidence': context['missing_evidence'],
                   'context_observability': {'budget_characters': budget, 'budget_exceeded': True,
                     'fallback_required': True, 'reason': 'core_facts_exceed_budget', 'retained_core_fields': list(core)}}
        return context
    # Keep lightweight original section aliases for existing citation consumers.
    for key in ('skill_results', 'modeling', 'optimization', 'cleaning', 'policy_receipt', 'standardization'):
        if size(context) > budget - 1500:
            replacement = core.get(key, {})
            context['run_evidence'][key] = deepcopy(replacement)
            context['context_observability']['truncated_fields'].append('run_evidence.' + key + ': optional detail only')
    if size(context) > budget - 1500:
        context['skill_context'] = []
        context['run_evidence'] = {'run_id': snapshot.get('run_id'), 'core_facts_ref': 'core_facts'}
        context['context_observability']['truncated_fields'].append('optional_skill_and_run_detail')
    for item in retrieval.get('documents', []):
        doc = {k: v for k, v in item.items() if k != 'excerpt'}
        if len(json.dumps(context, ensure_ascii=False, default=str)) + len(json.dumps(doc, ensure_ascii=False)) > budget:
            context['context_observability']['truncated_fields'].append('knowledge_context')
            break
        context['knowledge_context'].append(doc)
    context['context_observability']['knowledge_passed_count'] = len(context['knowledge_context'])
    return context


def ground_response(message, snapshot, response):
    context = build_answer_context(message, snapshot, response)
    response['answer_context'] = context
    response['capability_availability'] = context['capability_availability']
    response['missing_evidence'] = context['missing_evidence']
    response['used_run_evidence'] = []
    response['used_knowledge_chunks'] = []
    response['answer_sources'] = []
    # Append actual retrieved passages as clearly attributed method knowledge.
    # They remain data, cannot grant execution or override current-run numbers.
    for doc in context['knowledge_context'][:2]:
        if doc['category'] == 'historical_case':
            continue
        citation = f"knowledge:{doc['document_id']}:{doc['chunk_id']}"
        response['answer'] += f"\n\n方法资料（{doc['title']}，{doc.get('version') or '版本未记录'}）：{doc['relevant_excerpt']} [{citation}]"
        response['used_knowledge_chunks'].append(doc['chunk_id'])
        response['answer_sources'].append({'id': citation, **doc})
    topic = response.get('expert_topic') or (response.get('intent') or {}).get('key')
    section_map = {'snr': ['cleaning'], 'selection': ['cleaning'], 'degraded_modeling': ['cleaning', 'modeling'],
                   'order': ['modeling'], 'modeling': ['modeling'], 'lag': ['modeling'],
                   'cleaning': ['cleaning'], 'standardization': ['standardization'],
                   'optimization': ['optimization'], 'collinearity': ['modeling'], 'deployment': ['review']}
    sections = section_map.get(topic, list(snapshot.get('results', {})))
    # Citation allowlist must cover the current-run core facts actually sent to the model.
    sections = list(dict.fromkeys([*sections, *[key for key in ('cleaning', 'modeling', 'optimization', 'best_selection_receipt') if context.get('core_facts', {}).get(key) or key == 'best_selection_receipt' and context.get('core_facts', {}).get('selection')]]))
    if response.get('skill_plan', {}).get('analysis', {}).get('task_understanding', {}).get('task_kind') == 'knowledge_explanation':
        sections = []
    if snapshot.get('run_id'):
        for section in sections:
            if snapshot.get('results', {}).get(section):
                citation = f"run:{snapshot['run_id']}:{section}"
                response['used_run_evidence'].append(citation)
                response['answer_sources'].append({'id': citation, 'run_id': snapshot['run_id'], 'json_pointer': f'/results/{section}', 'source_type': 'current_run', 'stage': section, 'original_name': snapshot.get('original_name'), 'facts': context.get('run_evidence', {}).get(section) or context.get('core_facts', {}).get(section) or {'artifacts': snapshot.get('results', {}).get(section, {}).get('artifacts', {})}})
        if response.get('basic_data_profile'):
            citation = f"run:{snapshot['run_id']}:basic_data_profile"
            response['used_run_evidence'] = [citation]
            response['answer_sources'].append({'id': citation, 'run_id': snapshot['run_id'], 'source_type': 'raw_profile', 'provenance': response['basic_data_profile']['source'], 'facts': response['basic_data_profile'], 'original_name': snapshot.get('original_name')})
        for row in response.get('runtime_observability', {}).get('executor_results', []):
            if row.get('metrics'):
                citation = f"skill:{response.get('skill_run_id')}:{row.get('skill_id')}"
                response['used_run_evidence'].append(citation)
                response['answer_sources'].append({'id': citation, 'run_id': snapshot['run_id'], 'skill_run_id': response.get('skill_run_id'), 'skill_id': row.get('skill_id'), 'source_type': 'current_skill_execution', 'artifacts': row.get('artifacts', [])})
        if response['used_run_evidence']:
            response['answer'] += '\n\n当前运行证据：' + ' '.join(f'[{item}]' for item in response['used_run_evidence'])
    response['answer_mode'] = 'deterministic_evidence'
    return response
