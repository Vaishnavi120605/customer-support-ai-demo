"""Offline contract checks for the project quality gate; no Azure calls."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_PATH = ROOT / "quality" / "evaluation_scenarios.json"
INSTRUCTIONS_PATH = ROOT / "foundry" / "agent_instructions.py"
SCHEMA_PATH = ROOT / "database" / "schema.sql"


class OfflineQualityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))

    def test_scenario_catalog_is_valid_and_unique(self) -> None:
        self.assertGreaterEqual(len(self.scenarios), 10)
        ids = [scenario["id"] for scenario in self.scenarios]
        self.assertEqual(len(ids), len(set(ids)))
        for scenario in self.scenarios:
            self.assertTrue(scenario["required"])
            self.assertTrue(scenario["prompt"].strip())
            self.assertTrue(scenario["expected_behaviors"])

    def test_required_scenario_categories_are_covered(self) -> None:
        categories = {scenario["category"] for scenario in self.scenarios}
        self.assertTrue(
            {"grounded_order", "policy", "missing_order", "explicit_handoff", "privacy", "prompt_injection"}
            .issubset(categories)
        )

    def test_mandatory_handoffs_are_represented(self) -> None:
        categories = {scenario["category"] for scenario in self.scenarios}
        self.assertTrue({"refund_exception", "payment_dispute", "address_change", "damaged_item"}.issubset(categories))
        for scenario in self.scenarios:
            if scenario["category"] in {"refund_exception", "payment_dispute", "address_change", "damaged_item"}:
                self.assertIn("creates_handoff_ticket", scenario["expected_behaviors"])

    def test_agent_instructions_encode_grounding_and_handoff_rules(self) -> None:
        text = INSTRUCTIONS_PATH.read_text(encoding="utf-8").lower()
        for required_phrase in (
            "never invent order details",
            "use the order_lookup tool",
            "human handoff",
            "payment dispute",
            "damaged item",
            "do not expose another customer's data",
        ):
            self.assertIn(required_phrase, text)

    def test_schema_supports_auditable_handoff_lifecycle(self) -> None:
        text = SCHEMA_PATH.read_text(encoding="utf-8").lower()
        for required_phrase in ("create table if not exists handoff_tickets", "ai_summary", "assigned", "resolved", "create table if not exists audit_events"):
            self.assertIn(required_phrase, text)


if __name__ == "__main__":
    unittest.main()
