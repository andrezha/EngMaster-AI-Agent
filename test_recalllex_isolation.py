import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main
import utils


class RecallLexIsolationTests(unittest.TestCase):
    def test_default_windows_data_directory_is_independent(self):
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(
                utils.sys, "platform", "win32"), mock.patch.dict(
                    os.environ, {"APPDATA": temp_dir}, clear=False):
            os.environ.pop("RECALLLEX_DATA_DIR", None)
            utils.set_active_edition("gaokao")
            data_path = Path(utils.get_writable_data_path("mistake_words.json"))

        self.assertEqual(data_path.parent, Path(temp_dir) / "RecallLex")
        self.assertNotIn("EngMaster", str(data_path))

    def test_license_and_settings_use_recalllex_namespace(self):
        self.assertEqual(Path(main.get_license_path()).parent.name, ".RecallLex")
        self.assertEqual(main.SETTINGS_ORGANIZATION, "RecallLex")
        self.assertEqual(
            main.SETTINGS_APPLICATION, "YingSiChengVocabularyReview")


if __name__ == "__main__":
    unittest.main()
