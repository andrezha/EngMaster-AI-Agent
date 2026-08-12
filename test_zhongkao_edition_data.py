import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parent
EDITION = ROOT / "assets" / "editions" / "zhongkao"


class ZhongkaoEditionDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vocabulary = json.loads((EDITION / "vocabulary.json").read_text(encoding="utf-8"))
        cls.trial = json.loads((EDITION / "trial_vocabulary.json").read_text(encoding="utf-8"))
        cls.phrases = json.loads((EDITION / "phrases.json").read_text(encoding="utf-8"))
        cls.irregular = json.loads((EDITION / "irregular_verbs.json").read_text(encoding="utf-8"))
        cls.memory = json.loads((EDITION / "scientific_memory_data.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((EDITION / "manifest.json").read_text(encoding="utf-8"))
        cls.validation = json.loads((EDITION / "validation_report.json").read_text(encoding="utf-8"))

    def test_manifest_counts_match_product_files(self):
        counts = self.manifest["counts"]
        self.assertEqual(counts["vocabulary"], len(self.vocabulary))
        self.assertEqual(counts["trial_vocabulary"], 30)
        self.assertEqual(counts["phrases"], 250)
        self.assertEqual(counts["irregular_verbs"], 90)

    def test_vocabulary_is_unique_complete_and_pronounced(self):
        words = [row["word"].casefold() for row in self.vocabulary]
        self.assertEqual(len(words), len(set(words)))
        self.assertTrue(all(row.get("content") for row in self.vocabulary))
        self.assertTrue(all(row.get("pronunciation") for row in self.vocabulary))
        self.assertEqual(self.validation["coverage"]["unresolved_tokens"], [])
        self.assertEqual(self.validation["coverage"]["scope_tokens"], 1651)

    def test_trial_is_exact_formal_subset(self):
        by_word = {row["word"].casefold(): row for row in self.vocabulary}
        self.assertEqual(len(self.trial), 30)
        self.assertTrue(all(by_word[row["word"].casefold()] == row for row in self.trial))

    def test_scene_memory_is_selective_independent_and_duplicate_free(self):
        record_ids = [rid for group in self.memory["scene_groups"] for rid in group["records"]]
        self.assertEqual(len(record_ids), len(set(record_ids)))
        self.assertTrue(set(record_ids) < {row["record_id"] for row in self.vocabulary})
        self.assertGreaterEqual(len(record_ids), 600)
        self.assertTrue(all(2 <= len(group["records"]) <= 12 for group in self.memory["scene_groups"]))
        self.assertTrue(all(group["id"].startswith("junior_scene:") for group in self.memory["scene_groups"]))
        self.assertEqual(
            self.memory["scene_catalogue_policy"],
            "independently_curated_clear_junior_scenes_only",
        )

    def test_scene_examples_match_clear_junior_contexts(self):
        by_record = {row["record_id"]: row["word"] for row in self.vocabulary}
        theme_by_word = {
            by_record[rid].casefold(): group["title"].split(" · ", 1)[0]
            for group in self.memory["scene_groups"]
            for rid in group["records"]
        }
        expected = {
            "ruler": "课堂用品",
            "cream": "肉蛋奶饮品",
            "forest": "山川地貌",
            "beach": "山川地貌",
            "moon": "天空宇宙",
            "hospital": "医院就医",
            "supermarket": "购物消费",
            "firework": "节日庆祝",
            "penguin": "野生动物",
            "porridge": "主食小吃",
            "rocket": "天空宇宙",
            "humour": "幽默交流",
        }
        for word, theme in expected.items():
            self.assertEqual(theme_by_word[word], theme, word)
        for deliberately_unclassified in (
                "the", "because", "although", "under", "very",
                "post", "dining", "punish"):
            self.assertNotIn(deliberately_unclassified, theme_by_word)

    def test_required_public_licenses_are_present(self):
        for name in ("OPEN_ENGLISH_WORDNET_LICENSE.md", "PRINCETON_WORDNET_LICENSE.txt", "IPA_DICT_LICENSE.txt"):
            self.assertTrue((EDITION / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
