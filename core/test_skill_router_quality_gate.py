from django.test import SimpleTestCase

from training.skill_router.quality_gate import THRESHOLDS, check


class SkillRouterQualityGateTests(SimpleTestCase):
    def test_frozen_router_acceptance_passes_release_gate(self):
        result = check()
        self.assertEqual("passed", result["status"])
        self.assertTrue(all(result["checks"].values()))
        self.assertFalse(result["production_accuracy_claim"])
        self.assertGreaterEqual(result["observed"]["exact_skill_set_accuracy"], THRESHOLDS["exact_skill_set_accuracy"])
