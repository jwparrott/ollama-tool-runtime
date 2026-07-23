from __future__ import annotations

import unittest

from agent_runtime.skills import get_model_skill, list_model_skills


class SkillsTests(unittest.TestCase):
    def test_list_model_skills_contains_expected_entries(self) -> None:
        skills = list_model_skills()
        self.assertGreaterEqual(len(skills), 5)
        names = {skill["name"] for skill in skills}
        self.assertIn("code-review", names)
        self.assertIn("research", names)
        self.assertIn("new-tool-development", names)
        self.assertIn("conversation-memory-learning", names)
        self.assertIn("unstructured-conversation-parsing", names)

    def test_get_model_skill_exact_name(self) -> None:
        skill = get_model_skill("testing")
        self.assertEqual(skill["name"], "testing")
        self.assertIn("playbook", skill)
        self.assertTrue(skill["playbook"])

    def test_get_model_skill_case_insensitive(self) -> None:
        skill = get_model_skill("CoDe-ReViEw")
        self.assertEqual(skill["name"], "code-review")

    def test_get_model_skill_unknown_raises(self) -> None:
        with self.assertRaises(KeyError):
            get_model_skill("does-not-exist")


if __name__ == "__main__":
    unittest.main()
