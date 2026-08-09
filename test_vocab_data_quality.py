import json
import re
import unittest
from collections import Counter
from pathlib import Path


VOCAB_PATH = (
    Path(__file__).parent / "assets" / "editions" / "gaokao" / "vocabulary.json"
)


def load_vocab():
    return json.loads(VOCAB_PATH.read_text(encoding="utf-8"))


class VocabularyDataQualityTests(unittest.TestCase):
    def test_vocabulary_schema_and_pronunciation_fields_are_complete(self):
        rows = load_vocab()
        self.assertEqual(len(rows), 3800)
        self.assertEqual(len({row["record_id"] for row in rows}), 3800)
        self.assertTrue(all(
            row["word"].strip() and row["content"].strip() for row in rows
        ))
        self.assertTrue(all(
            re.search(r"[\u3400-\u9fff]", row["content"]) for row in rows
        ))
        self.assertTrue(all(
            row.get("pronunciation", "").startswith("/")
            and row["pronunciation"].endswith("/")
            and row.get("pronunciation_source") == "ipa-dict en_US"
            for row in rows
        ))
        self.assertEqual(
            Counter(row["pronunciation_match_method"] for row in rows),
            {
                "direct": 3781,
                "spelling_alias": 8,
                "derived": 10,
                "sense_variant_addition": 1,
            },
        )

    def test_headwords_do_not_contain_scraped_pronunciation_fragments(self):
        rows = load_vocab()
        self.assertFalse([
            row["word"]
            for row in rows
            if re.search(r"[/\[*]$", row["word"])
            or re.search(r"（.*(?:比较级|最高级|复).*）", row["word"])
        ])

    def test_known_heteronyms_keep_multiple_pronunciations(self):
        by_word = {row["word"]: row for row in load_vocab()}
        for word in (
            "bow", "close", "conduct", "content", "desert", "lead", "live",
            "minute", "object", "present", "produce", "project", "refuse",
            "row", "subject", "tear", "use", "wind", "wound",
        ):
            self.assertIn(",", by_word[word]["pronunciation"], word)
        self.assertEqual(by_word["row"]["pronunciation"], "/ˈɹoʊ/, /ˈɹaʊ/")

    def test_known_non_direct_matches_remain_traceable(self):
        by_word = {row["word"]: row for row in load_vocab()}
        self.assertEqual(
            by_word["analyse"]["pronunciation_match_method"],
            "spelling_alias",
        )
        self.assertEqual(
            by_word["according to"]["pronunciation_match_method"],
            "derived",
        )
        self.assertEqual(by_word["PE"]["pronunciation"], "/ˌpiˈi/")
        self.assertEqual(
            by_word["stomachache"]["pronunciation"],
            "/ˈstəməkˌeɪk/",
        )


if __name__ == "__main__":
    unittest.main()
