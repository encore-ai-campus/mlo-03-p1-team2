"""Regression checks for synthetic profile diversity and reproducibility."""

import copy
import unittest

from generatePersonas import generate_personas, validate_dataset


class PersonaGenerationTests(unittest.TestCase):
    def test_names_are_unique_without_numeric_suffixes(self):
        for seed in (0, 42, 2026):
            with self.subTest(seed=seed):
                users = generate_personas(1000, seed)["users"]
                names = [user["name"] for user in users]
                self.assertEqual(len(set(names)), 1000)
                self.assertTrue(all(name.isalpha() for name in names))

    def test_seed_reproduces_profiles(self):
        self.assertEqual(generate_personas(), generate_personas())
        self.assertNotEqual(generate_personas(seed=0), generate_personas(seed=42))

    def test_validator_rejects_duplicate_names(self):
        data = copy.deepcopy(generate_personas())
        data["users"][1]["name"] = data["users"][0]["name"]
        with self.assertRaisesRegex(ValueError, "Duplicate name"):
            validate_dataset(data)

    def test_same_persona_has_different_styles_and_introductions(self):
        users = generate_personas()["users"]
        for persona in {user["persona"] for user in users}:
            group = [user for user in users if user["persona"] == persona]
            with self.subTest(persona=persona):
                self.assertEqual(len({u.get("bio") for u in group}), len(group))
                for field in ("companion", "attendance_frequency", "discovery_style"):
                    self.assertGreater(len({u["viewing_style"][field] for u in group}), 1)
                for user in group:
                    self.assertTrue(all(c in user["bio"] for c in user["preferred_categories"]))
                    self.assertNotIn("\n", user["bio"])

    def test_validator_rejects_introduction_inconsistent_with_style(self):
        data = generate_personas()
        data["users"][0]["bio"] = "취향과 무관한 소개"
        with self.assertRaisesRegex(ValueError, "bio"):
            validate_dataset(data)


if __name__ == "__main__":
    unittest.main()
