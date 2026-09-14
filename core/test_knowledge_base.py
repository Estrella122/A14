import json

from django.core.management import call_command
from django.test import TestCase

from core.models import KnowledgeDocument, KnowledgeEntity, RoutingFeedback, SkillKnowledgeRule
from core.services.knowledge_base import search_knowledge
from core.skills.catalog import SKILLS
from core.skills.runtime import plan_skills


class KnowledgeBaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_knowledge_base', verbosity=0)

    def test_seed_covers_three_official_scenes_and_every_skill(self):
        self.assertEqual(KnowledgeEntity.objects.filter(entity_type='scene', status='approved').count(), 3)
        self.assertEqual(SkillKnowledgeRule.objects.filter(status='approved').count(), len(SKILLS))
        self.assertEqual(KnowledgeDocument.objects.filter(status='approved').count(), 4)

    def test_seed_is_idempotent(self):
        call_command('seed_knowledge_base', verbosity=0)
        self.assertEqual(SkillKnowledgeRule.objects.count(), len(SKILLS))
        self.assertEqual(KnowledgeDocument.objects.count(), 4)

    def test_search_returns_scene_entity_skill_and_provenance(self):
        result = search_knowledge('提取脱丁烷塔高信噪比动态段', 'debutanizer_column')
        skill_ids = {row['skill_id'] for row in result['skill_suggestions']}
        entity_ids = {row['entity_id'] for row in result['entities']}
        self.assertIn('high_snr_dynamic_segment_extractor', skill_ids)
        self.assertIn('scene:debutanizer_column', entity_ids)
        self.assertTrue(result['provenance'])

    def test_negative_term_blocks_simulation_rule(self):
        result = search_knowledge('不要生成仿真数据，只分析现有数据')
        skill_ids = {row['skill_id'] for row in result['skill_suggestions']}
        self.assertNotIn('industrial_simulation_generator', skill_ids)

    def test_casual_query_does_not_produce_skill_suggestion(self):
        self.assertEqual(search_knowledge('你好，今天怎么样')['skill_suggestions'], [])

    def test_agent_plan_exposes_auditable_knowledge_context(self):
        plan = plan_skills('请提取脱丁烷塔高信噪比动态段')
        retrieval = plan['analysis']['knowledge_retrieval']
        self.assertEqual(retrieval['retrieval_mode'], 'structured_lexical_v1')
        self.assertIn('builtin-skill-routing-v1', retrieval['provenance'])
        self.assertIn('high_snr_dynamic_segment_extractor', [row['skill_id'] for row in retrieval['skill_suggestions']])

    def test_knowledge_does_not_confuse_residual_cross_correlation_with_process_lag(self):
        plan = plan_skills('残差是否为白噪声，请结合残差自相关和残差与输入互相关说明')
        suggested = {row['skill_id'] for row in plan['analysis']['knowledge_retrieval']['skill_suggestions']}
        selected = {row['skill_id'] for row in plan['steps']}
        self.assertNotIn('time_delay_estimator_compensator', suggested)
        self.assertNotIn('time_delay_estimator_compensator', selected)
        self.assertIn('model_diagnostics_evaluator', selected)

    def test_summary_search_and_feedback_apis(self):
        summary = self.client.get('/api/knowledge/summary/').json()['data']
        self.assertEqual(summary['skill_coverage']['covered'], len(SKILLS))
        search = self.client.get('/api/knowledge/search/', {'q': '高炉时滞补偿', 'scene_id': 'blast_furnace'})
        self.assertEqual(search.status_code, 200)
        response = self.client.post('/api/knowledge/feedback/', data=json.dumps({
            'query': '高炉时滞补偿', 'scene_id': 'blast_furnace',
            'predicted_skill_ids': ['time_delay_estimator_compensator'],
            'corrected_skill_ids': [], 'outcome': 'accepted',
        }), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(RoutingFeedback.objects.count(), 1)

    def test_feedback_rejects_unknown_skill(self):
        response = self.client.post('/api/knowledge/feedback/', data=json.dumps({
            'query': '测试', 'predicted_skill_ids': ['made_up_skill'],
            'corrected_skill_ids': [], 'outcome': 'accepted',
        }), content_type='application/json')
        self.assertEqual(response.status_code, 400)
