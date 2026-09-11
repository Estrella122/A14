from __future__ import annotations

import pandas as pd
from django.test import SimpleTestCase

from integrations.standardization.standard_agent.demo import generate_demo
from integrations.standardization.standard_agent.engine import StandardizationAgent
from integrations.standardization.standard_agent.repository import ScenarioRepository


class SceneRecognitionAccuracyTests(SimpleTestCase):
    """Behavior tests for evidence-based recognition, independent of literal fixtures."""

    def setUp(self):
        self.agent = StandardizationAgent(ScenarioRepository())

    def test_01_normal_scene_is_confirmed(self):
        result = self.agent.standardize(generate_demo("blast_furnace", rows=80, seed=11))
        self.assertEqual(result["detection"]["final_scene"], "blast_furnace")
        self.assertEqual(result["detection"]["status"], "confirmed")

    def test_02_single_abnormal_field_does_not_create_a_new_scene(self):
        frame = generate_demo("blast_furnace", rows=80, seed=12)
        column = "Th"
        frame[column] = 1_000_000
        result = self.agent.standardize(frame)
        self.assertEqual(result["detection"]["selected"]["scenario_id"], "blast_furnace")
        self.assertTrue(any("abnormal_values" in item for item in result["detection"]["selected"]["conflicts"]))

    def test_03_multiple_abnormal_fields_reduce_confidence(self):
        normal = generate_demo("industrial_dryer", rows=80, seed=13)
        baseline = self.agent.standardize(normal)["detection"]["confidence"]
        corrupted = normal.copy()
        for name in list(corrupted.columns)[1:4]:
            corrupted[name] = 1_000_000
        result = self.agent.standardize(corrupted)
        self.assertLess(result["detection"]["confidence"], baseline)
        self.assertNotEqual(result["detection"]["status"], "confirmed")

    def test_04_different_names_with_same_semantics_use_registry_aliases(self):
        frame = generate_demo("industrial_dryer", rows=60, seed=14)
        aliases = {field.display_name: field.aliases[0] for field in self.agent.repository.get("industrial_dryer").fields if field.aliases}
        renamed = frame.rename(columns={name: aliases[name] for name in frame.columns if name in aliases})
        result = self.agent.standardize(renamed)
        self.assertEqual(result["detection"]["final_scene"], "industrial_dryer")

    def test_05_same_generic_names_on_different_equipment_are_not_decisive(self):
        frame = pd.DataFrame({"time": range(30), "temperature": range(30), "pressure": range(30), "flow": range(30)})
        result = self.agent.standardize(frame, instruction="未知设备测试")
        self.assertIn(result["detection"]["status"], {"uncertain", "ambiguous", "unknown"})
        self.assertIsNone(result["detection"]["final_scene"])

    def test_06_convertible_units_keep_semantics_and_values_plausible(self):
        frame = generate_demo("blast_furnace", rows=60, seed=16)
        frame["Th(°F)"] = frame.pop("Th") * 9 / 5 + 32
        result = self.agent.standardize(frame)
        self.assertEqual(result["detection"]["final_scene"], "blast_furnace")

    def test_07_missing_required_fields_cannot_be_confirmed(self):
        frame = generate_demo("blast_furnace", rows=60, seed=17)
        required = self.agent.repository.get("blast_furnace").recognition["required_features"]
        mapping = self.agent.map_columns(list(frame.columns), "blast_furnace")
        raw_by_standard = {item["standard"]: item["raw"] for item in mapping["mappings"]}
        frame = frame.drop(columns=[raw_by_standard[name] for name in required[:5]])
        result = self.agent.standardize(frame)
        self.assertNotEqual(result["detection"]["status"], "confirmed")

    def test_08_invalid_values_are_reported_as_conflicts(self):
        frame = generate_demo("industrial_dryer", rows=60, seed=18)
        numeric = frame.select_dtypes(include="number").columns[0]
        frame[numeric] = frame[numeric].astype(object)
        frame.loc[:30, numeric] = "invalid"
        result = self.agent.standardize(frame)
        self.assertTrue(result["detection"]["selected"]["conflicts"])

    def test_09_similar_scene_scores_become_ambiguous(self):
        left = generate_demo("industrial_dryer", rows=60, seed=19)
        right = generate_demo("blast_furnace", rows=60, seed=20)
        overlap = pd.concat([left, right.drop(columns=right.columns[0])], axis=1)
        overlap = overlap.loc[:, ~overlap.columns.duplicated()]
        result = self.agent.standardize(overlap)
        self.assertEqual(result["detection"]["status"], "ambiguous")
        self.assertIsNone(result["detection"]["final_scene"])

    def test_10_unknown_scene_is_not_forced(self):
        frame = pd.DataFrame({"batch_uuid": ["a", "b"], "operator_note": ["ok", "ok"], "image_hash": [1, 2]})
        result = self.agent.standardize(frame)
        self.assertEqual(result["detection"]["status"], "unknown")
        self.assertIsNone(result["detection"]["final_scene"])
