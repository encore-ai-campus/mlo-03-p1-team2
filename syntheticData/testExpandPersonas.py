"""Appending profiles must preserve all prior identities and be repeatable."""
import copy
import unittest

from generatePersonas import expand_personas, generate_personas, validate_dataset


class ExpansionTests(unittest.TestCase):
    def test_append_preserves_prior_profiles_and_balances_the_result(self):
        original = generate_personas(100)
        snapshot = copy.deepcopy(original)
        expanded = expand_personas(original, 300)
        self.assertEqual(original, snapshot)
        self.assertEqual(expanded['users'][:100], snapshot['users'])
        self.assertEqual(len(expanded['users']), 300)
        self.assertEqual(expanded['metadata']['count'], 300)
        validate_dataset(expanded)

    def test_append_is_reproducible_and_idempotent(self):
        original = generate_personas(100)
        result = expand_personas(original, 300)
        self.assertEqual(result, expand_personas(original, 300))
        self.assertEqual(result, expand_personas(result, 300))

    def test_shrinking_never_discards_profiles(self):
        with self.assertRaises(ValueError):
            expand_personas(generate_personas(100), 99)


if __name__ == '__main__':
    unittest.main()
