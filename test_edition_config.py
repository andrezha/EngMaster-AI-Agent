import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from edition_config import (
    EDITIONS,
    PAGE_PHRASE_CHALLENGE,
    PAGE_PHRASE_LIST,
    RELEASED_EDITION_IDS,
    edition_was_explicitly_requested,
    extract_edition_args,
    resolve_edition,
)
from utils import get_writable_data_path, set_active_edition


ROOT = Path(__file__).parent


class EditionConfigTests(unittest.TestCase):
    def tearDown(self):
        set_active_edition("gaokao")

    def test_four_expected_editions_are_registered(self):
        self.assertEqual(
            set(EDITIONS), {"zhongkao", "gaokao", "cet4", "cet6", "kaoyan"}
        )
        self.assertTrue(EDITIONS["gaokao"].production_ready)
        self.assertFalse(EDITIONS["zhongkao"].production_ready)
        self.assertFalse(EDITIONS["cet4"].production_ready)
        self.assertFalse(EDITIONS["cet6"].production_ready)
        self.assertFalse(EDITIONS["kaoyan"].production_ready)
        self.assertEqual(RELEASED_EDITION_IDS, ("gaokao",))

    def test_fixed_product_word_counts_are_shown_without_approximation(self):
        expected = {
            "zhongkao": 1600,
            "gaokao": 3800,
            "cet4": 4500,
            "cet6": 5500,
            "kaoyan": 5500,
        }
        for edition_id, count in expected.items():
            edition = EDITIONS[edition_id]
            self.assertEqual(edition.word_count, count)
            self.assertIn(str(count), edition.product_title)
            self.assertIn(f"（{count}词）", edition.challenge_title)
            self.assertNotIn("约", edition.product_title)

    def test_every_edition_enables_phrase_and_irregular_pages(self):
        for edition in EDITIONS.values():
            self.assertTrue(edition.page_enabled(PAGE_PHRASE_CHALLENGE))
            self.assertTrue(edition.page_enabled(PAGE_PHRASE_LIST))
            self.assertTrue((ROOT / edition.phrase_path).is_file())
            self.assertTrue((ROOT / edition.irregular_verbs_path).is_file())

    def test_zhongkao_uses_its_own_phrase_candidate(self):
        edition = EDITIONS["zhongkao"]
        self.assertEqual(
            edition.phrase_path,
            "research/edition_samples/zhongkao_phrases.json",
        )
        rows = json.loads((ROOT / edition.phrase_path).read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 90)
        self.assertTrue(
            all(row.get("p") and row.get("m") for row in rows)
        )
        self.assertTrue(
            all(row.get("edition") == "zhongkao" for row in rows)
        )

    def test_zhongkao_uses_reduced_irregular_verb_candidate(self):
        edition = EDITIONS["zhongkao"]
        self.assertEqual(
            edition.irregular_verbs_path,
            "research/edition_samples/zhongkao_irregular_verbs.json",
        )
        rows = json.loads(
            (ROOT / edition.irregular_verbs_path).read_text(encoding="utf-8")
        )
        self.assertEqual(len(rows), 90)
        self.assertTrue(
            all(
                row.get("infinitive")
                and row.get("past_tense")
                and row.get("past_participle")
                for row in rows
            )
        )
        infinitives = {row["infinitive"] for row in rows}
        self.assertTrue({"be", "go", "do", "have", "write", "bite", "freeze"} <= infinitives)
        self.assertFalse({"burst", "steal", "swing"} & infinitives)

    def test_advanced_editions_use_independent_phrase_and_irregular_files(self):
        master_rows = json.loads(
            (ROOT / "assets" / "short_phrase.json").read_text(encoding="utf-8"))
        phrase_paths = {
            EDITIONS[edition_id].phrase_path
            for edition_id in ("gaokao", "cet4", "cet6", "kaoyan")
        }
        irregular_paths = {
            EDITIONS[edition_id].irregular_verbs_path
            for edition_id in ("gaokao", "cet4", "cet6", "kaoyan")
        }
        self.assertEqual(len(phrase_paths), 4)
        self.assertEqual(len(irregular_paths), 4)
        for edition_id in ("gaokao", "cet4", "cet6", "kaoyan"):
            rows = json.loads(
                (ROOT / EDITIONS[edition_id].phrase_path).read_text(encoding="utf-8"))
            if edition_id == "gaokao":
                self.assertEqual(len(rows), 450)
                self.assertEqual(
                    sum(row.get("tier") == "core" for row in rows), 300)
                self.assertEqual(
                    sum(row.get("tier") == "extension" for row in rows), 150)
                self.assertEqual(
                    max(row.get("level", 0) for row in rows[:300]), 6)
                self.assertEqual(
                    max(row.get("level", 0) for row in rows[300:]), 3)
            else:
                self.assertEqual(len(rows), len(master_rows))
                self.assertEqual(
                    sum(row.get("tier") == "core" for row in rows), 350)
                self.assertEqual(
                    sum(row.get("tier") == "extension" for row in rows), 150)
                self.assertEqual(
                    sum(row.get("tier") == "candidate" for row in rows),
                    max(0, len(master_rows) - 500))

    def test_development_vocabulary_files_exist_and_have_expected_counts(self):
        expected_counts = {
            "zhongkao": 30,
            "gaokao": 3800,
            "cet4": 30,
            "cet6": 30,
            "kaoyan": 30,
        }
        for edition_id, edition in EDITIONS.items():
            path = ROOT / edition.vocabulary_path
            rows = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(rows), expected_counts[edition_id])
            self.assertTrue(all(row.get("word") and row.get("content") for row in rows))

    def test_cli_edition_option_is_removed_before_qt(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            edition, cleaned = extract_edition_args(
                ["main.py", "--edition", "cet4", "--watermark-mode=licensed"]
            )
        self.assertEqual(edition.edition_id, "cet4")
        self.assertEqual(cleaned, ["main.py", "--watermark-mode=licensed"])
        self.assertEqual(resolve_edition("CET6").edition_id, "cet6")

    def test_startup_selector_is_skipped_for_explicit_edition(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(
                edition_was_explicitly_requested(["main.py", "--edition=cet6"])
            )
            self.assertTrue(
                edition_was_explicitly_requested(["main.py", "--edition", "cet4"])
            )
            self.assertFalse(edition_was_explicitly_requested(["main.py"]))
        with mock.patch.dict(
            os.environ, {"ENGMASTER_EDITION": "zhongkao"}, clear=True
        ):
            self.assertTrue(edition_was_explicitly_requested(["main.py"]))

    def test_new_editions_have_isolated_writable_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(
                os.environ, {"ENGMASTER_DATA_DIR": temp_dir}, clear=False
            ):
                set_active_edition("gaokao")
                gaokao = Path(get_writable_data_path("progress.json"))
                set_active_edition("zhongkao")
                zhongkao = Path(get_writable_data_path("progress.json"))
                set_active_edition("cet4")
                cet4 = Path(get_writable_data_path("progress.json"))

        self.assertEqual(gaokao.parent, Path(temp_dir))
        self.assertEqual(zhongkao.parent, Path(temp_dir) / "editions" / "zhongkao")
        self.assertEqual(cet4.parent, Path(temp_dir) / "editions" / "cet4")


if __name__ == "__main__":
    unittest.main()
