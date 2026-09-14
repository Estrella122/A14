"""Execution intent and artifact readiness are independent contracts."""
from tempfile import TemporaryDirectory
from django.test import SimpleTestCase, override_settings
from acceptance.evaluate_real_routing import predicted_stop
from core.skills.runtime import plan_skills
from core.test_skill_md_runtime import snapshot_fixture


class PlanningExecutionModeTests(SimpleTestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.snapshot=snapshot_fixture(self.temp.name)

    def check(self,text,execute,stage=None):
        for mode in ['legacy','hybrid','md']:
            for snapshot in [None,self.snapshot]:
                with self.subTest(text=text,mode=mode,has_snapshot=snapshot is not None), override_settings(SKILL_MANIFEST_MODE=mode):
                    p=plan_skills(text,snapshot=snapshot)
                    self.assertEqual('execute' if execute else 'analyze',p['mode'])
                    if not execute:
                        self.assertEqual('evidence_only',predicted_stop(p))
                        if p['analysis'].get('routing_source')=='md_registry':
                            self.assertEqual([],p['analysis'].get('execution_plan',{}).get('core',{}).get('steps',[]))
                    elif stage:
                        self.assertEqual(stage,predicted_stop(p))
                    if execute and mode=='md':
                        nodes=p['analysis']['execution_plan']['core']['steps']
                        self.assertTrue(nodes)
                        if snapshot is None:
                            self.assertTrue(any(n['readiness_status']=='blocked' for n in nodes))

    def test_cleaning_evidence(self):self.check('查看清洗结果',False)
    def test_cleaning_execute(self):self.check('重新执行数据清洗',True,'cleaning')
    def test_selection_evidence(self):self.check('为什么筛选成这样',False)
    def test_selection_execute(self):self.check('重新提取高信噪比动态段',True,'selection')
    def test_modeling_evidence(self):self.check('当前模型指标如何',False)
    def test_modeling_execute(self):self.check('训练系统辨识模型',True,'modeling')
    def test_reidentify_question_is_not_action(self):self.check('哪些参数需要重新辨识',False)
    def test_model_why_question_is_evidence(self):self.check('为什么当前模型结果这样',False)
    def test_explicit_model_identification_action(self):self.check('请重新运行模型辨识',True)

    def test_original_stage_requests_keep_execution_intent_without_data(self):
        for text,stage in [('清洗缺失值','cleaning'),('提取高信噪比动态段','selection'),('训练系统辨识模型','modeling')]:
            self.check(text,True,stage)
