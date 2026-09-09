"""Intent guards and multi-clause selection around the supervised router."""
from __future__ import annotations
import re
from .catalog import SKILL_MAP
from .router_model import normalize, predict

NEGATIVE = re.compile(r'^(?:(?:请|我|麻烦|务必|千万|一定|现在|暂时|先|这次|本次)\s*)*(?:不要|别|不必|无需|禁止|不需要|不用|不能|不得|停止|取消|do not|don\x27t)\s*', re.I)
ACTION = re.compile(r'^(?:(?:请|麻烦|劳驾|帮我|帮忙|给我|替我|我需要|我想|现在|立即|先|再|然后|只|仅|把|将|对|进行|执行)\s*)*(?:重新执行|重新运行|重跑|运行一遍|提取|筛选|清洗|规整|生成|创建|合成|模拟|训练|建立|拟合|优化|寻优|导出|下载|打包|处理|补齐|修复|剔除|计算|估计|抽取|选择|选取|组装|拼接|冻结|标记|检测|绘制|画|撰写|编写|整理|起草|按\d+秒|resample|train|fit|generate|export|download|plot)')
QUESTION = re.compile(r'为什么|为何|怎么|如何|是否|能否|可以.*吗|什么|哪个|哪些|多少|多大|怎么样|如果|假如|假设|假定|假若|假想|倘若|假使|假如|what\b|why\b|how\b', re.I)
FULL_RUN = re.compile(r'^(?:(?:请|帮我|现在|立即|开始|重新)\s*)*(?:重新执行|重新运行|重跑|运行一遍|执行全流程|运行全流程|跑一遍完整流程)(?:当前任务|全流程|流水线|一遍|全部)?[。！!\s]*$')
SUPPORT = {'industrial_intent_parser','skill_capability_matcher','workflow_dag_planner','execution_supervisor_replanner','equipment_entity_resolver','constraint_parameter_extractor'}


def clauses(message):
    text=normalize(message)
    if re.search(r'按钮|字符串|这句话|原话|原文|引用|他说|她说|提示词|关键字',text):
        text=re.sub(r'“[^”]*”|"[^"]*"|「[^」]*」|‘[^’]*’', '',text)
    text=re.sub(r'(?:之后|以后|后)(?=进行|执行|再|开始)', '，',text)
    parts=re.split(r'[，,；;。！？!?\n]+|(?:然后|并且|以及|同时|接着)|(?<=\S)再(?=训练|执行|导出|提取|优化)|(?<=\S)并(?=训练|执行|导出|提取|优化)',text)
    return [p.strip() for p in parts if p.strip()]


def select(message: str, analysis: dict, expert_rules, topic_keys):
    parts=clauses(message)
    negative=[];positive=[]
    for part in parts:
        if NEGATIVE.match(part):negative.append(NEGATIVE.sub('',part))
        elif re.search(r'(?:不要|不必|无需|禁止|不需要|不用|不能|不得).{0,15}(?:执行|运行|重跑|训练|清洗|导出|生成|提取)',part):negative.append(part)
        else:positive.append(part)
    normalized_message = normalize(message)
    full_run=bool(
        FULL_RUN.fullmatch(normalized_message)
        or (
            re.search(r'(?:重新执行|重新运行|重跑|执行|运行|跑一遍).{0,8}(?:全流程|完整流程|流水线)', normalized_message)
            and not negative
            and not QUESTION.search(message)
        )
    )
    # Questions and hypothetical/quoted instructions never authorize a pipeline.
    explicit=any(ACTION.search(p) or re.search(r'^(?:(?:请|帮我|现在|立即|先|再)\s*)*(?:开始执行|立即执行|重新执行|重新运行|运行一遍|重跑)|^(?:请|帮我)?(?:把|将|对).{1,35}(?:重采样|补齐|清洗|提取|导出|训练|绘制)',p) for p in positive)
    question=bool(QUESTION.search(message) or re.search(r'会不会|能不能|可不可以|要不要|[?？吗呢]\s*$',message))
    expert_request=question or bool(re.search(r'^(?:请)?(?:分析|说明|解释)',normalize(message)))
    mode='execute' if (explicit and not question) or full_run else 'analyze'
    selected=set();scores={};decisions=[];unknown=[]
    for part in positive:
        result=predict(part)
        # Grammar resolves the requested action/object before statistical
        # ranking: drawing residuals is a chart task, not model retraining.
        prefix=r'^(?:(?:请|帮我|给我|我需要|只|仅|现在|先|再)\s*)*'
        forced=None
        if re.search(prefix+r'(?:下载|导出|打包|获取.{0,20}下载|提供.{0,20}下载)',part):
            forced='final_artifact_exporter'
        elif re.search(prefix+r'(?:撰写|编写|起草|写).{0,40}(?:报告|文档|评审稿|评审材料)',part):
            forced='expert_report_writer'
        elif re.search(prefix+r'(?:画|绘制|展示|生成).{0,40}(?:图|曲线|可视化)',part):
            forced='engineering_visualization_builder'
        if forced:
            result.update(skill_id=forced,accepted=True,reason='explicit_action_grammar',model_score=result['score'],score=1.0,score_type='explicit_action_rule')
            if forced not in {candidate['skill_id'] for candidate in result['candidates']}:
                result['candidates'].insert(0,{'skill_id':forced,'score':1.0})
        decisions.append({'text':part,**result})
        if result['skill_id'] and result['skill_id'] not in SKILL_MAP:
            raise ValueError('Router model contains an unknown skill ID')
        if result['skill_id']:
            selected.add(result['skill_id']);scores[result['skill_id']]=result['score']
        elif len(part)>=4:
            unknown.append(part)
    # Exact registered IDs are explicit routing requests, with token boundaries.
    for part in positive:
        for skill_id in SKILL_MAP:
            if skill_id not in SUPPORT and re.search(r'(?<![a-z0-9_])'+re.escape(skill_id)+r'(?![a-z0-9_])',part):
                selected.add(skill_id);scores[skill_id]=1.
    expert_topics={'leakage','residual','stability','frequency','causality','generalization','order','optimization','reproducibility','deployment','transfer','drift','excitation','degraded_modeling'}
    use_expert=mode=='analyze' and expert_request and bool(set(analysis['topics'])&expert_topics)
    if use_expert:
        # Retain the curated evidence requirements of expert reviews; do not
        # promote a topic mentioned only inside a denied action.
        selected=set();scores={}
        active='，'.join(positive)
        for topic,(terms,ids) in zip(topic_keys,expert_rules):
            hits=[term for term in terms if term.lower() in active]
            if hits:
                selected.update(ids);scores.update({sid:0.86 for sid in ids})
        unknown=[]
    denied=set()
    for part in negative:
        result=predict(part)
        # Rejection is conservative: a negative command may suppress a likely
        # target even when below the acceptance threshold; it can never add one.
        if result['top_label'] in SKILL_MAP:denied.add(result['top_label'])
        for sid in SKILL_MAP:
            if sid in part:denied.add(sid)
    selected-=denied
    if full_run:
        selected={'closed_loop_preprocessing_optimizer','expert_report_writer'}
        scores.update({s:1. for s in selected});unknown=[]
    # A negative-only or unrecognized message is a clarification, never a
    # report-writing fallback. Positive known clauses remain visible for review.
    needs_clarification=not selected or (mode=='execute' and bool(unknown))
    if needs_clarification:mode='analyze'
    # Model score is evidence of ranking, not a fabricated confidence interval.
    return {'direct':selected,'scores':scores,'mode':mode,'decisions':decisions,
            'denied':denied,'needs_clarification':needs_clarification,'unresolved_clauses':unknown,
            'source':'expert_evidence_contract' if use_expert else 'trained_linear_router',
            'full_pipeline_requested':full_run,
            'negative_clauses':negative}
