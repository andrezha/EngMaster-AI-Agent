import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from phrase_irregular_module import PhraseIrregularChallengeView


ROOT = Path(__file__).parent
CANDIDATE_DIR = ROOT / "data_sources/clean/phrase_product_candidates"
EXPECTED = {"junior": 250, "senior_high": 450, "cet4": 750, "cet6": 1050}


class PhraseProductCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_candidates_have_application_schema_and_counts(self):
        for edition_id, expected_count in EXPECTED.items():
            path = CANDIDATE_DIR / f"{edition_id}_phrases_product_candidate.json"
            rows = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(rows), expected_count)
            self.assertTrue(all(row["p"] and row["m"] and row["en"] and row["cn"] for row in rows))
            self.assertTrue(all(row["answers"][0] == row["p"] for row in rows))
            self.assertTrue(all(row["tier"] == "core" for row in rows))
            self.assertTrue(all(row["human_review_claimed"] is False for row in rows))

    def test_cet6_challenge_wraps_twenty_one_levels_into_three_rows(self):
        with tempfile.TemporaryDirectory() as data_dir, mock.patch.dict(
            os.environ, {"ENGMASTER_DATA_DIR": data_dir}
        ):
            edition = SimpleNamespace(
                edition_id="cet6",
                phrase_path="data_sources/clean/phrase_product_candidates/cet6_phrases_product_candidate.json",
                irregular_verbs_path="assets/editions/gaokao/irregular_verbs.json",
            )
            view = PhraseIrregularChallengeView(SimpleNamespace(edition=edition))
            self.assertEqual(len(view.phrase_levels), 21)
            self.assertEqual(len(view.phrase_level_buttons), 21)
            self.assertEqual(view.phrase_level_panel.layout().count(), 3)
            view.close()


if __name__ == "__main__":
    unittest.main()
