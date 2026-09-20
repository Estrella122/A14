from __future__ import annotations

import hashlib

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import (
    KnowledgeAlias, KnowledgeChunk, KnowledgeDocument, KnowledgeEntity,
    KnowledgeRelation, SkillKnowledgeRule,
)
from core.services.knowledge_base import normalize_text
from core.services.scene_registry import list_scene_configs
from core.skills.catalog import SKILLS
from core.skills.contracts import get_skill_contract


SCENE_KNOWLEDGE = {
    'blast_furnace': {
        'summary': '钢铁高炉以铁水硅含量为关键质量变量，典型输入包括鼓风流量、热风温度、富氧率、压差和矿焦比。小时级采样下应重点检查慢时滞、工况切换和跨炉况泛化。',
        'keywords': ['高炉', '铁水', '硅含量', '鼓风流量', '热风温度', '富氧率', '矿焦比'],
        'variables': [('铁水硅含量', 'output'), ('鼓风流量', 'input'), ('热风温度', 'input'), ('富氧率', 'input'), ('矿焦比', 'disturbance')],
    },
    'debutanizer_column': {
        'summary': '脱丁烷精馏塔以塔底 C4 浓度为软测量目标，常用变量包括回流流量、塔顶压力、第六层塔板温度和塔底温度，过程通常存在分钟级纯滞后。',
        'keywords': ['脱丁烷塔', '精馏塔', '塔底C4浓度', '回流流量', '塔顶压力', '塔板温度', '软测量'],
        'variables': [('塔底C4浓度', 'output'), ('回流流量', 'input'), ('塔顶压力', 'disturbance'), ('第六层塔板温度', 'input'), ('塔底温度', 'input')],
    },
    'industrial_dryer': {
        'summary': '工业干燥器是多输入多输出热质传递过程，热风入口温度与风量是主要操纵量，湿料进料量是扰动，产品含水率、产品温度和排风湿度是主要输出。',
        'keywords': ['工业干燥器', '干燥机', '热风入口温度', '风量', '湿料进料量', '产品含水率', '排风湿度'],
        'variables': [('产品含水率', 'output'), ('产品温度', 'output'), ('排风湿度', 'output'), ('热风入口温度', 'input'), ('热风流量', 'input'), ('湿料进料量', 'disturbance')],
    },
    'steel_industry_energy': {
        'summary': '钢铁工业能源数据以有功用电量为预测目标，滞后/超前无功电量和功率因数描述负载电气特性。该公开数据适合能耗预测与动态数据质量分析，但没有可直接下发的工艺操纵量，不能把相关性模型解释为生产闭环控制模型。',
        'keywords': ['钢铁工业能源', '有功用电量', '滞后无功电量', '超前无功电量', '功率因数', '负载类型', '能耗预测'],
        'variables': [('有功用电量', 'output'), ('滞后无功电量', 'input'), ('超前无功电量', 'input'), ('滞后功率因数', 'state'), ('超前功率因数', 'state'), ('负载类型', 'context')],
    },
    'thermal_power_boiler_long_tail': {
        'summary': '燃煤工业锅炉长尾数据以锅炉出口蒸汽温度为主要输出，包含炉膛压力、氧量、风量、减温水与蒸汽流量等变量。专业分析应区分单步预测、自由仿真和闭环可用性，并在时滞补偿后复算VIF，避免把共同扰动当作因果操纵关系。',
        'keywords': ['燃煤工业锅炉', '锅炉出口蒸汽温度', '炉膛压力', '减温水流量', '主蒸汽流量', '时滞', 'VIF'],
        'variables': [('锅炉出口蒸汽温度', 'output'), ('一次减温水流量', 'input'), ('一次风机出口流量', 'input'), ('补偿主蒸汽流量', 'disturbance'), ('炉膛压力', 'state'), ('省煤器入口烟气氧量', 'state')],
    },
    'vapor_pressure_soft_sensor': {
        'summary': '蒸气压力软测量数据以小时序列记录温度、流量、压力和阀位，实测蒸气压力是稀疏化验目标。应从累计小时派生相对时间轴，目标缺失不得插值成真值；时滞、共线性和软测量模型只能在真实观测目标上训练与评估。',
        'keywords': ['蒸气压力软测量', '实测蒸气压力', '累计小时', '稀疏化验', 'Antoine压力估计', '再沸器平均温度'],
        'variables': [('实测蒸气压力', 'output'), ('累计小时', 'time'), ('再沸器平均温度', 'input'), ('冷凝压力逆变换', 'input'), ('Antoine压力估计', 'input'), ('当前压力估计', 'input')],
    },
}

BOUNDARIES = {
    'industrial_simulation_generator': {'positive': ['仿真数据', '生成测试数据', '合成数据'], 'negative': ['不要生成', '无需生成', '不生成', '分析现有数据']},
    'steady_transient_state_detector': {'positive': ['稳态', '瞬态', '过渡态', '工况切换'], 'negative': []},
    'high_snr_dynamic_segment_extractor': {'positive': ['高信噪比动态段', '动态段提取', '提取动态数据'], 'negative': ['不要提取']},
    'collinearity_detector_reducer': {'positive': ['共线性', '共线', 'VIF', '冗余变量'], 'negative': ['因果关系', '根因']},
    'time_delay_estimator_compensator': {'positive': ['时滞', '纯滞后', '延迟补偿', '互相关'], 'negative': ['残差与输入互相关', '残差互相关']},
    'model_diagnostics_evaluator': {'positive': ['残差诊断', '白噪声检验', 'Ljung-Box', '稳定极点'], 'negative': []},
    'closed_loop_preprocessing_optimizer': {'positive': ['闭环寻优', '预处理寻优', '目标权重', '收敛条件'], 'negative': ['不要寻优']},
    'expert_report_writer': {'positive': ['专家报告', '评审报告', '生成报告'], 'negative': ['不要报告', '无需报告']},
    'final_artifact_exporter': {'positive': ['导出产物', '下载结果', '交付包'], 'negative': ['不要导出']},
}


class Command(BaseCommand):
    help = '幂等写入已支持工业场景、变量实体及全部 Skill 路由知识。'

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()
        from core.services.implementation_knowledge import IMPLEMENTATION_NOTES
        for key, title, uri, locator, keywords, body in IMPLEMENTATION_NOTES:
            digest = hashlib.sha256(body.encode()).hexdigest()
            document, _ = KnowledgeDocument.objects.get_or_create(
                document_id=f"implementation-{key}-{digest[:12]}", defaults={
                    'title': title, 'source_type': 'implementation_note', 'source_uri': uri,
                    'scene_id': '', 'version': digest[:12], 'status': 'approved',
                    'approved_by': 'implementation_contract_review', 'checksum': digest, 'effective_at': now})
            KnowledgeChunk.objects.get_or_create(chunk_id=f"implementation-{key}-{digest[:12]}", defaults={
                'document': document, 'ordinal': 1, 'content': body, 'keywords': keywords,
                'metadata': {'category': 'algorithm_knowledge', 'source_locator': locator,
                             'external_industrial_review': False}})

        scene_count = 0
        variable_count = 0
        registered_scenes = {row['id']: row for row in list_scene_configs()}
        for scene_id, curated in SCENE_KNOWLEDGE.items():
            scene = registered_scenes[scene_id]
            body = curated['summary']
            document, _ = KnowledgeDocument.objects.update_or_create(
                document_id=f"builtin-scene-{scene['id']}-v1",
                defaults={'title': f"{scene['name']}场景知识", 'source_type': 'builtin_reviewed',
                          'source_uri': 'frontend/src/data/scenes.json', 'scene_id': scene['id'],
                          'version': '1.0', 'status': 'approved', 'approved_by': 'system_seed',
                          'effective_at': now, 'checksum': hashlib.sha256(body.encode()).hexdigest()},
            )
            KnowledgeChunk.objects.update_or_create(
                chunk_id=f"scene-{scene['id']}-overview", defaults={
                    'document': document, 'ordinal': 1, 'content': body,
                    'keywords': curated['keywords'], 'metadata': {'kind': 'scene_overview', 'reviewed': True},
                })
            scene_entity, _ = KnowledgeEntity.objects.update_or_create(
                entity_id=f"scene:{scene['id']}", defaults={
                    'entity_type': 'scene', 'canonical_name': scene['name'], 'scene_id': scene['id'],
                    'attributes': {'family': scene['family'], 'official': bool(scene.get('official')), 'supported': True}, 'status': 'approved',
                    'source_document': document,
                })
            for alias in {scene['name'], scene['id'], *scene.get('aliases', [])}:
                KnowledgeAlias.objects.update_or_create(
                    entity=scene_entity, normalized_alias=normalize_text(alias),
                    defaults={'alias': alias, 'priority': 90})
            scene_count += 1
            for name, role in curated['variables']:
                slug = hashlib.sha1(name.encode()).hexdigest()[:12]
                entity, _ = KnowledgeEntity.objects.update_or_create(
                    entity_id=f"variable:{scene['id']}:{slug}", defaults={
                        'entity_type': 'variable', 'canonical_name': name, 'scene_id': scene['id'],
                        'attributes': {'role': role}, 'status': 'approved', 'source_document': document,
                    })
                KnowledgeAlias.objects.update_or_create(
                    entity=entity, normalized_alias=normalize_text(name), defaults={'alias': name, 'priority': 80})
                KnowledgeRelation.objects.update_or_create(
                    relation_id=f"{entity.entity_id}:belongs_to:{scene['id']}", defaults={
                        'subject': entity, 'predicate': 'belongs_to_scene', 'object_entity': scene_entity,
                        'confidence': 1, 'status': 'approved', 'source_document': document,
                    })
                variable_count += 1

        routing_body = '由 Skill catalog 和独立执行契约生成；规则仅参与候选加权，不能绕过否定词、质量门禁或人工审批。'
        routing_doc, _ = KnowledgeDocument.objects.update_or_create(
            document_id='builtin-skill-routing-v1', defaults={
                'title': 'ProcessPilot Skill 路由知识', 'source_type': 'generated_from_contracts',
                'source_uri': 'core/skills/catalog.py', 'version': '1.0', 'status': 'approved',
                'approved_by': 'system_seed', 'effective_at': now,
                'checksum': hashlib.sha256(routing_body.encode()).hexdigest(),
            })
        KnowledgeChunk.objects.update_or_create(
            chunk_id='skill-routing-governance-v1', defaults={
                'document': routing_doc, 'ordinal': 1, 'content': routing_body,
                'keywords': ['Skill路由', '能力匹配', '否定词', '质量门禁', '人工审批'],
                'metadata': {'kind': 'governance'},
            })
        for skill in SKILLS:
            contract = get_skill_contract(skill.id)
            boundary = BOUNDARIES.get(skill.id, {})
            positive = list(dict.fromkeys([term for term in skill.triggers if term != '*'] + boundary.get('positive', [])))
            negative = boundary.get('negative', [])
            entity, _ = KnowledgeEntity.objects.update_or_create(
                entity_id=f"skill:{skill.id}", defaults={
                    'entity_type': 'skill', 'canonical_name': skill.name, 'scene_id': '',
                    'attributes': {'category': skill.category, 'description': skill.description,
                                   'handler': skill.handler, 'version': skill.version},
                    'status': 'approved', 'source_document': routing_doc,
                })
            for alias in {skill.id, skill.name}:
                KnowledgeAlias.objects.update_or_create(
                    entity=entity, normalized_alias=normalize_text(alias), defaults={'alias': alias, 'priority': 95})
            SkillKnowledgeRule.objects.update_or_create(
                rule_id=f"skill-route:{skill.id}:v1", defaults={
                    'skill_id': skill.id, 'scene_id': '', 'intent_patterns': boundary.get('positive', []),
                    'positive_terms': positive, 'negative_terms': negative,
                    'requires_artifacts': list(contract.requires) if contract else [], 'priority': 80,
                    'confidence': 0.84, 'status': 'approved',
                    'rationale': f"{skill.description} 来源于已版本化 Skill 定义与执行契约。",
                    'source_document': routing_doc, 'version': skill.version,
                })
        self.stdout.write(self.style.SUCCESS(
            f'知识库已就绪：{scene_count} 个支持场景，{variable_count} 个变量，{len(SKILLS)} 条 Skill 规则。'))
