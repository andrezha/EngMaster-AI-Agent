# -*- coding: utf-8 -*-
import json
import random
import tempfile
import unittest
from pathlib import Path

from challenge_rounds import ChallengeRoundStore
import phrase_irregular_module


class IrregularVerbVariantTests(unittest.TestCase):
    def test_wake_uses_one_space_between_forms(self):
        self.assertTrue(
            phrase_irregular_module._is_accepted_verb_answer(
                "woke waked", "woke, waked"))
        self.assertTrue(
            phrase_irregular_module._is_accepted_verb_answer(
                "woken waked", "woken, waked"))
        self.assertFalse(
            phrase_irregular_module._is_accepted_verb_answer(
                "woke", "woke, waked"))
        self.assertTrue(
            phrase_irregular_module._is_accepted_verb_answer(
                "woke   waked", "woke, waked"))
        self.assertFalse(
            phrase_irregular_module._is_accepted_verb_answer(
                "wakedwoke", "woke, waked"))

    def test_legacy_fullwidth_commas_are_supported(self):
        expected = "waked，woken，woke"
        self.assertEqual(
            phrase_irregular_module._clean_verb_field(expected),
            "waked woken woke",
        )
        self.assertTrue(
            phrase_irregular_module._is_accepted_verb_answer(
                "waked woken woke", expected))

    def test_every_multi_form_field_uses_spaces_only(self):
        with open(
                "assets/irregular_verbs.json", "r", encoding="utf-8") as handle:
            verbs = json.load(handle)

        multi_form_fields = 0
        for verb in verbs:
            for field in ("past_tense", "past_participle"):
                expected = verb[field]
                variants = phrase_irregular_module._verb_variants(expected)
                if len(variants) > 1:
                    multi_form_fields += 1
                    self.assertTrue(
                        phrase_irregular_module._is_accepted_verb_answer(
                            phrase_irregular_module._clean_verb_field(expected),
                            expected,
                        ),
                        f"{verb['infinitive']} {field}",
                    )
        self.assertGreater(multi_form_fields, 0)

    def test_wake_wording_change_preserves_current_round_progress(self):
        old_items = [
            {
                "infinitive": "wake",
                "past_tense": "waked，woke",
                "past_participle": "waked，woken，woke",
                "meaning": "醒来",
            },
            {
                "infinitive": "write",
                "past_tense": "wrote",
                "past_participle": "written",
                "meaning": "写",
            },
        ]
        new_items = [
            {
                "infinitive": "wake",
                "past_tense": "woke, waked",
                "past_participle": "woken, waked",
                "meaning": "醒来",
            },
            old_items[1],
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rounds.json"
            store = ChallengeRoundStore(path, rng=random.Random(7))
            store.activate("irregular", old_items)
            before = store.progress("irregular")
            current_infinitive = store.current_items("irregular")[0]["infinitive"]

            reopened = ChallengeRoundStore(path, rng=random.Random(9))
            reopened.activate("irregular", new_items)

            self.assertEqual(reopened.progress("irregular"), before)
            self.assertEqual(
                reopened.current_items("irregular")[0]["infinitive"],
                current_infinitive,
            )


if __name__ == "__main__":
    unittest.main()
