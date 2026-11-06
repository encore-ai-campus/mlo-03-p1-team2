import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from syntheticData.generatePersonas import generate_personas
from syntheticData.playwright.load_preparation import expand_file, profiles_for_run
from syntheticData.playwright.scenarios import save_profiles_snapshot


class PreparationTests(unittest.TestCase):
    def test_new_period_campaign_can_resolve_its_older_source_input(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = root / 'original.json'
            original.write_text(json.dumps(generate_personas(100)), encoding='utf-8')
            current = root / 'personas.json'
            current.write_text(json.dumps(generate_personas(300)), encoding='utf-8')
            directory = root / 'new-period'
            directory.mkdir()
            (directory / 'state.json').write_text(json.dumps({'fingerprint': {
                'profiles_sha256': hashlib.sha256(original.read_bytes()).hexdigest()}}), encoding='utf-8')
            save_profiles_snapshot(directory, original)
            self.assertEqual(profiles_for_run(directory, current).read_bytes(), original.read_bytes())
            with self.assertRaises(ValueError):
                save_profiles_snapshot(directory, current)

    def test_expansion_preserves_historical_input_bytes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            profile = root / 'personas.json'
            raw = json.dumps(generate_personas(100), ensure_ascii=False, indent=2).encode('utf-8')
            profile.write_bytes(raw)
            history = root / 'artifacts' / 'old'
            history.mkdir(parents=True)
            (history / 'state.json').write_text(json.dumps({'fingerprint': {
                'profiles_sha256': hashlib.sha256(raw).hexdigest()}}), encoding='utf-8')
            expand_file(profile, root / 'artifacts')
            self.assertEqual(profiles_for_run(history, profile).read_bytes(), raw)
            first = profile.read_bytes()
            self.assertEqual(len(json.loads(first)['users']), 300)
            expand_file(profile, root / 'artifacts')
            self.assertEqual(profile.read_bytes(), first)

    def test_historical_hash_mismatch_stops_without_changing_profiles(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            profile = root / 'personas.json'
            raw = json.dumps(generate_personas()).encode()
            profile.write_bytes(raw)
            history = root / 'artifacts' / 'old'
            history.mkdir(parents=True)
            (history / 'state.json').write_text(json.dumps({'fingerprint': {'profiles_sha256': 'bad'}}))
            with self.assertRaises(ValueError):
                expand_file(profile, root / 'artifacts')
            self.assertEqual(profile.read_bytes(), raw)
