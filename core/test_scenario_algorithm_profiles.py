import sys
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from core.services.pipeline import _candidate_score, _effective_max_lag
from integrations.standardization.standard_agent.repository import ScenarioRepository


BASE_DIR = Path(settings.BASE_DIR)
OFFICIAL_SCENES = ("blast_furnace", "debutanizer_column", "industrial_dryer")


class ScenarioAlgorithmProfileTests(SimpleTestCase):
    def setUp(self):
        self.repository = ScenarioRepository()

    def test_three_official_scenes_have_versioned_complete_profiles(self):
        for scene_id in OFFICIAL_SCENES:
            with self.subTest(scene_id=scene_id):
                profile = self.repository.get(scene_id).summary()["algorithm_profile"]
                self.assertEqual(profile["version"], "1.0.0")
                self.assertIn(profile["validation_status"], {
                    "validated_on_project_real_data",
                    "engineering_baseline_pending_real_data_acceptance",
                })
                self.assertEqual(set(profile), {"version", "validation_status", "selection", "decoupling", "optimization"})
                self.assertAlmostEqual(sum(profile["selection"]["score_weights"].values()), 1.0)
                self.assertAlmostEqual(sum(profile["optimization"]["objective_weights"].values()), 1.0)
                self.assertGreaterEqual(len(profile["optimization"]["candidates"]), 6)

    def test_scene_profiles_are_not_one_shared_default(self):
        profiles = {scene_id: self.repository.get(scene_id).summary()["algorithm_profile"] for scene_id in OFFICIAL_SCENES}
        self.assertEqual(profiles["blast_furnace"]["selection"]["window_samples"], 24)
        self.assertEqual(profiles["debutanizer_column"]["selection"]["window_samples"], 120)
        self.assertEqual(profiles["industrial_dryer"]["selection"]["window_samples"], 18)
        self.assertEqual(profiles["blast_furnace"]["decoupling"]["max_lag_samples"], 12)
        self.assertEqual(profiles["debutanizer_column"]["decoupling"]["max_lag_samples"], 90)
        self.assertEqual(profiles["industrial_dryer"]["decoupling"]["max_lag_samples"], 18)

    def test_effective_lag_uses_scene_contract_and_physical_delay(self):
        expected = {"blast_furnace": 12, "debutanizer_column": 90, "industrial_dryer": 18}
        for scene_id, lag in expected.items():
            with self.subTest(scene_id=scene_id):
                scenario = self.repository.get(scene_id).summary()
                self.assertEqual(_effective_max_lag(60, scenario), lag)

    def test_selection_executor_accepts_scene_policy(self):
        module_path = str(BASE_DIR / "integrations/data_cleaning/src")
        sys.path.insert(0, module_path)
        try:
            from data_cleaning_agent import DataCleaningSelectionAgent

            policy = self.repository.get("blast_furnace").summary()["algorithm_profile"]["selection"]
            agent = DataCleaningSelectionAgent({}, selection_window=policy["window_samples"], selection_step=policy["step_samples"], selection_policy=policy)
        finally:
            sys.path.remove(module_path)
        self.assertEqual(agent.selection_window, 24)
        self.assertEqual(agent.selection_step, 6)
        self.assertEqual(agent.selection_policy["snr_db"], 6)
        self.assertEqual(agent.selection_policy["score_weights"]["output_response"], 0.30)

    def test_optimization_score_reads_scene_objective_weights(self):
        metrics = {"r2": 0.5, "rmse": 1.0}
        coverage_first = _candidate_score(metrics, 0.8, {"r2": 0.1, "error": 0.1, "coverage": 0.8})
        fit_first = _candidate_score(metrics, 0.8, {"r2": 0.8, "error": 0.1, "coverage": 0.1})
        self.assertNotEqual(coverage_first, fit_first)
