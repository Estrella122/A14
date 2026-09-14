"""Candidate identity checks, independent of numeric range plausibility.

Final acceptance is applied to every scenario; physical contracts provide additional dimensions.
Declared aliases and point dictionaries are curated identity evidence; model and
fuzzy candidates must independently establish the critical physical dimensions.
"""
import re

TRUSTED = {'alias', 'normalized_alias', 'learned_alias', 'point_dictionary'}


def source_semantics(name):
    text = re.sub(r'[_/.-]+', ' ', name.lower())
    def has(pattern): return bool(re.search(pattern, text))
    quantities = [q for q, pattern in [('temperature', r'\b(temp|temperature)\b|温度|顶温|底温'), ('pressure', r'\b(pressure|press)\b|压力'), ('flow', r'\bflow\b|流量')] if has(pattern)]
    quantity = quantities[0] if len(quantities) == 1 else ('conflict' if quantities else None)
    # Conflicting equipment/location words take precedence over generic column words.
    locations = []
    for pattern, location in [(r'\breboiler\b|重沸器','reboiler_outlet'),(r'\bfeed\b|进料','feed'),(r'\btop\b|塔顶','column_top'),(r'\bbottom\b|塔底','column_bottom'),(r'\btray\s*6\b|\bsixth\s+tray\b|第六塔板','tray_6')]:
        if has(pattern): locations.append(location)
    if has(r'\btray\s*(?!6\b)\d+\b'): locations.append('other_tray')
    location = locations[0] if len(locations)==1 else ('conflict' if locations else None)
    directions=[]
    for pattern,direction in [(r'\b(feed|inlet)\b|进料|入口','inlet'),(r'\breflux\b|回流','reflux'),(r'\brecycle\b|再循环','recycle'),(r'\bdownstream\b|\bnext\s+process\b|下游|后续流程','downstream'),(r'\boutlet\b|出口|出料','outlet')]:
        if has(pattern):directions.append(direction)
    if set(directions)=={'downstream','outlet'}:directions=['downstream']
    direction=directions[0] if len(directions)==1 else ('conflict' if directions else None)
    if quantity=='flow' and location is None and direction in {'reflux','downstream'}:
        location={'reflux':'reflux_line','downstream':'downstream_line'}[direction]
    channels = [c for c in ('a', 'b') if has(r'\b' + c + r'\b')]
    channel = channels[0] if len(channels) == 1 else ('conflict' if channels else None)
    return {'quantity_type':quantity,'physical_role':('setpoint' if has(r'\b(setpoint|sp|target)\b|设定') else 'process_measurement') if quantity else None,
            'equipment_role':'other_equipment' if has(r'\b(furnace|dryer|boiler|reactor)\b|高炉|干燥器|锅炉|反应器') else 'reboiler' if 'reboiler_outlet' in locations else ('feed_line' if 'feed' in locations else ('column' if location else None)),
            'measurement_location':location,'flow_direction':direction,'measurement_channel':channel}


def evaluate(raw, target, method, confidence, unit_status, contract, threshold):
    standard=contract.get(target,{})
    trusted=method in TRUSTED
    observed=source_semantics(raw)
    # Curated identity fills unknown dimensions, never overwrites contradictory tokens.
    source={**standard, **{k:v for k,v in observed.items() if v is not None}} if trusted else observed
    def evidence(key, required=True):
        expected=standard.get(key); actual=source.get(key)
        ok=bool(expected is not None and actual is not None and expected==actual) if required else True
        return {'source':actual,'expected':expected,'compatible':ok,'basis':'curated_identity' if trusted else 'source_name_tokens'}
    quantity=evidence('quantity_type'); role=evidence('physical_role'); location=evidence('measurement_location')
    location['equipment']=evidence('equipment_role')
    location['channel']=evidence('measurement_channel',bool(standard.get('measurement_channel')))
    direction=evidence('flow_direction',standard.get('quantity_type')=='flow')
    unit={'status':unit_status,'compatible':unit_status in {'consistent','convertible'} or (trusted and unit_status=='not_declared'), 'basis':'declared_header_unit' if unit_status!='not_declared' else ('curated_contract_unit' if trusted else 'unknown')}
    gates={'semantic_similarity_pass':confidence>=threshold,'unit_compatible':unit['compatible'],
           'quantity_type_compatible':quantity['compatible'],'physical_role_compatible':role['compatible'],
           'location_compatible':location['compatible'] and location['equipment']['compatible'] and location['channel']['compatible'],
           'direction_compatible':direction['compatible'],'source_confidence_pass':trusted or (bool(standard) and confidence>=threshold and source.get('equipment_role')=='column')}
    # Exact aliases stay subject to existing unit/value gates; noncritical identities
    # (timestamp/index) are supported by the curated alias instead of token inference.
    if trusted and not standard:
        # Nonphysical identifiers still require identity/unit checks in the final gate.
        for key in gates:
            if key not in {'semantic_similarity_pass','unit_compatible'}:gates[key]=True
    failures=[key for key,value in gates.items() if not value]
    return {'physical_gate_pass':not failures,'physical_gates':gates,
            'source_confidence_evidence':{'pass':gates['source_confidence_pass'],'basis':'curated_identity' if trusted else 'explicit_source_tokens_and_candidate_score; not provenance verification'},
            'semantic_evidence':{'method':method,'confidence':confidence,'identity_basis':'curated_alias_or_point' if trusted else 'candidate_only; values are not identity evidence'},
            'unit_evidence':unit,'quantity_type_evidence':quantity,'role_evidence':role,
            'location_evidence':location,'direction_evidence':direction,
            'physical_decision_reason':'physical gates satisfied' if not failures else 'physical gates require review: '+', '.join(failures)}


def final_field_acceptance_gate(item, template, threshold, source_metadata=None):
    """The sole final acceptance decision, including aliases and manual bindings.

    Metadata is field-scoped and scenario-bound. Anonymous/scaled channels need
    documented identity AND units; scaled values also need an applied transform
    receipt, never an inferred inverse based on their numeric range.
    """
    metadata = source_metadata or {}
    target = item.get('standard')
    definition = template.by_name.get(target)
    method = item.get('method', '')
    raw = item.get('base_name', item.get('raw', ''))
    contract = template.config.get('physical_semantics', {})
    trusted = method in TRUSTED
    anonymous = bool(re.fullmatch(r'(?:[uxy]\d*|(?:normalized|scaled|column|feature)[_ -]*\d+)', raw.strip(), re.I))
    scoped = bool(metadata.get('evidence_source') and metadata.get('standard_field') == target
                  and metadata.get('scenario_id') == template.scenario_id)
    identity = bool(definition and (trusted or method == 'manual' or item.get('confidence', 0) >= threshold))
    if anonymous or method == 'normalization_mapping':
        identity = scoped
    unit_status = item.get('unit_status', 'not_declared')
    if scoped and metadata.get('unit') == item.get('expected_unit') and unit_status == 'not_declared':
        unit_status = 'consistent'
    unit_ok = unit_status in {'consistent', 'convertible'} or (trusted and not anonymous and unit_status == 'not_declared')
    scaling_ok = not (anonymous or metadata.get('normalized')) or bool(scoped and metadata.get('unit') and
        (metadata.get('normalized') is False or (metadata.get('inverse_metadata') and metadata.get('transform_applied'))))
    if target and contract:
        physical = evaluate(raw, target, 'alias' if scoped else method, item.get('confidence', 0), unit_status, contract, threshold)
    else:
        observed = source_semantics(raw)
        expected = source_semantics(target or '')
        dimensions = {k: not (observed.get(k) and expected.get(k) and observed[k] != expected[k])
                      for k in expected}
        physical = {'physical_gate_pass': all(dimensions.values()), 'physical_gates': dimensions,
                    'physical_decision_reason': 'explicit source/canonical dimensions checked; unspecified dimensions rely on curated identity'}
        # No unconstrained semantic/model/manual binding without a physical contract.
        if not trusted:
            physical['physical_gate_pass'] = False
    point = item.get('point_resolution', {})
    point_ok = method != 'point_dictionary' or (point.get('status') == 'resolved' and point.get('scene') == template.scenario_id and point.get('standard_field') == target and bool(point.get('source')))
    if method == 'point_dictionary' and point.get('unit') and point['unit'] != item.get('expected_unit'):
        from .units import conversion
        point_ok = point_ok and bool(conversion(point['unit'], item.get('expected_unit')))
    expected = contract.get(target, {})
    metadata_dimensions = {key: not (metadata.get(key) is not None and expected.get(key) is not None and metadata[key] != expected[key]) for key in ['quantity_type', 'physical_role', 'equipment_role', 'measurement_location', 'measurement_channel', 'flow_direction']}
    if metadata.get('unit'):
        from .units import conversion
        metadata_dimensions['unit'] = metadata['unit'] == item.get('expected_unit') or bool(conversion(metadata['unit'], item.get('expected_unit')))
    gates = {'metadata_consistency': all(metadata_dimensions.values()), 'point_dictionary_binding': bool(point_ok), 'candidate_exists': bool(definition), 'identity_basis': identity,
             'unit': unit_ok and bool(definition and item.get('expected_unit') == definition.unit), 'physical_semantics': physical['physical_gate_pass'],
             'source_confidence': item.get('confidence', 0) >= threshold,
             'provenance': not anonymous or scoped, 'normalization_metadata': scaling_ok,
             'scenario_compatibility': not metadata.get('scenario_id') or metadata['scenario_id'] == template.scenario_id}
    failures = [k for k,v in gates.items() if not v]
    decision = 'AUTO_ACCEPT' if not failures else 'REVIEW_REQUIRED' if definition else 'REJECT'
    reason = 'final gate passed' if not failures else 'final gate requires review: ' + ', '.join(failures)
    audit = {'gate': 'final_field_acceptance_gate', 'method': method, 'source_column': item.get('raw'),
             'candidate': target, 'scenario': template.scenario_id, 'required_field_criticality': bool(definition and definition.required),
             'identity_basis': 'scoped_source_metadata' if scoped else 'curated_identity' if trusted and not anonymous else 'candidate_only',
             'provenance_level': 'documented' if scoped else 'registry_identity' if trusted and not anonymous else 'unverified',
             'unit_basis': 'source_metadata' if scoped else 'declared_header' if item.get('detected_unit') else 'registry_unit' if trusted and not anonymous else 'unknown',
             'checks': gates, 'physical_checks': physical.get('physical_gates', {}),
             'source_metadata': metadata, 'metadata_checks': metadata_dimensions,
             'physical_evidence': {k:v for k,v in physical.items() if k.endswith('_evidence')}, 'decision': decision, 'reason': reason}
    return {**physical, 'physical_gate_pass': not failures, 'decision': decision,
            'decision_reason': reason, 'final_acceptance_audit': audit,
            'status': 'matched' if decision == 'AUTO_ACCEPT' else 'review' if definition else 'unmapped'}
