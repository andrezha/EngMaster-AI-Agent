import json
import random
import tempfile
import time
import unittest
from pathlib import Path

from challenge_rounds import (
    ChallengeLearningStore,
    ChallengeRoundStore,
    backup_existing_file_once,
    backup_learning_upgrade_once,
)


class ChallengeRoundStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_path = str(Path(self.temp_dir.name) / "rounds.json")
        self.items = [{"word": word} for word in ["a", "b", "c", "d"]]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_round_has_no_repeats_and_next_round_resets_counters(self):
        store = ChallengeRoundStore(self.state_path, rng=random.Random(7))
        active = store.activate("regular", self.items)
        seen = []
        first_word = active[0]["word"]

        while True:
            seen.append(active[0]["word"])
            if active[0]["word"] == first_word:
                store.mark_wrong("regular")
                store.mark_wrong("regular")
            summary, active = store.advance("regular", self.items)
            if summary:
                break

        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(set(seen), {"a", "b", "c", "d"})
        self.assertEqual(summary["round"], 1)
        self.assertEqual(summary["wrong"], 1)
        self.assertEqual(store.progress("regular")["round"], 2)
        self.assertEqual(store.progress("regular")["wrong"], 0)
        self.assertEqual(store.progress("regular")["current"], 1)

    def test_progress_survives_restart(self):
        first = ChallengeRoundStore(self.state_path, rng=random.Random(2))
        active = first.activate("regular", self.items)
        first_word = active[0]["word"]
        first.mark_wrong("regular")
        first.advance("regular", self.items)

        restored = ChallengeRoundStore(self.state_path, rng=random.Random(99))
        restored_active = restored.activate("regular", self.items)
        self.assertNotEqual(restored_active[0]["word"], first_word)
        self.assertEqual(restored.progress("regular")["current"], 2)
        self.assertEqual(restored.progress("regular")["wrong"], 1)

    def test_wrong_question_requires_retry_after_restart_until_advanced(self):
        first = ChallengeRoundStore(self.state_path, rng=random.Random(21))
        first.activate("regular", self.items)
        current_word = first.current_items("regular")[0]["word"]
        first.mark_wrong("regular")
        self.assertTrue(first.is_retry_required("regular"))

        restored = ChallengeRoundStore(self.state_path, rng=random.Random(22))
        restored.activate("regular", self.items)
        self.assertEqual(restored.current_items("regular")[0]["word"], current_word)
        self.assertTrue(restored.is_retry_required("regular"))

        restored.advance("regular", self.items)
        self.assertFalse(restored.is_retry_required("regular"))

    def test_version_one_current_wrong_item_migrates_to_retry_required(self):
        seed = ChallengeRoundStore(self.state_path, rng=random.Random(23))
        seed.activate("regular", self.items)
        data = json.loads(Path(self.state_path).read_text(encoding="utf-8"))
        state = data["modes"]["regular"]
        state["wrong"] = [state["remaining"][0]]
        state.pop("retry_key", None)
        data["version"] = 1
        Path(self.state_path).write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8")

        migrated = ChallengeRoundStore(self.state_path, rng=random.Random(24))
        migrated.activate("regular", self.items)
        self.assertTrue(migrated.is_retry_required("regular"))

    def test_new_items_wait_until_the_next_round(self):
        initial = self.items[:2]
        expanded = self.items[:3]
        store = ChallengeRoundStore(self.state_path, rng=random.Random(3))
        active = store.activate("self_register", initial)
        active = store.activate("self_register", expanded)
        self.assertNotIn("c", {item["word"] for item in active})

        while True:
            summary, active = store.advance("self_register", expanded)
            if summary:
                break
        self.assertEqual({item["word"] for item in active}, {"a", "b", "c"})

    def test_two_store_instances_do_not_overwrite_each_others_modes(self):
        word_store = ChallengeRoundStore(self.state_path, rng=random.Random(1))
        phrase_store = ChallengeRoundStore(self.state_path, rng=random.Random(2))
        word_store.activate("regular", self.items)
        phrase_store.activate("phrase", [{"p": "look up"}, {"p": "give up"}])
        word_store.mark_wrong("regular")

        data = json.loads(Path(self.state_path).read_text(encoding="utf-8"))
        self.assertIn("regular", data["modes"])
        self.assertIn("phrase", data["modes"])

    def test_damaged_round_state_rebuilds_without_touching_study_items(self):
        Path(self.state_path).write_text(
            json.dumps({
                "version": 1,
                "modes": {
                    "regular": {
                        "round": "broken",
                        "completed": None,
                        "remaining": "not-a-list",
                        "wrong": {"bad": "shape"},
                    }
                },
            }),
            encoding="utf-8",
        )
        original_items = json.loads(json.dumps(self.items))
        store = ChallengeRoundStore(self.state_path, rng=random.Random(5))
        active = store.activate("regular", self.items)
        self.assertEqual({item["word"] for item in active}, {"a", "b", "c", "d"})
        self.assertEqual(self.items, original_items)
        self.assertEqual(store.progress("regular")["round"], 1)

    def test_backup_is_one_time_and_does_not_change_source(self):
        source = Path(self.temp_dir.name) / "mistake_words.json"
        source.write_text('[{"word":"kept"}]', encoding="utf-8")
        backup = Path(backup_existing_file_once(str(source)))
        source.write_text('[{"word":"new"}]', encoding="utf-8")
        backup_existing_file_once(str(source))

        self.assertEqual(backup.read_text(encoding="utf-8"), '[{"word":"kept"}]')
        self.assertEqual(source.read_text(encoding="utf-8"), '[{"word":"new"}]')

    def test_learning_history_preserves_legacy_start_and_records_completion(self):
        learning_path = str(Path(self.temp_dir.name) / "learning.json")
        store = ChallengeLearningStore(learning_path)
        progress = {"round": 3, "current": 20, "total": 100, "wrong": 4}
        store.ensure_round("regular", progress, started_before_tracking=True)
        store.resume("regular")
        pending = store.snapshot()["modes"]["regular"]["ongoing"]
        self.assertIsNone(pending["tracking_started_at"])
        self.assertEqual(pending["active_seconds"], 0)
        store.begin_round("regular")
        store.resume("regular")
        time.sleep(0.05)
        store.pause("regular")
        snapshot = store.snapshot()
        ongoing = snapshot["modes"]["regular"]["ongoing"]
        self.assertTrue(ongoing["started_before_tracking"])
        self.assertIsNone(ongoing["started_at"])
        self.assertGreater(ongoing["active_seconds"], 0)

        store.finish_round("regular", {"round": 3, "total": 100, "wrong": 4})
        completed = store.snapshot()["modes"]["regular"]["history"][0]
        self.assertEqual(completed["round"], 3)
        self.assertEqual(completed["wrong"], 4)
        self.assertEqual(completed["status"], "completed")
        self.assertTrue(completed["ended_at"])

    def test_new_round_starts_only_after_first_challenge_action(self):
        learning_path = str(Path(self.temp_dir.name) / "learning.json")
        store = ChallengeLearningStore(learning_path)
        store.ensure_round(
            "regular", {"round": 1, "current": 1, "total": 10, "wrong": 0})
        store.resume("regular")
        pending = store.snapshot()["modes"]["regular"]["ongoing"]
        self.assertIsNone(pending["started_at"])
        self.assertIsNone(pending["tracking_started_at"])
        store.begin_round("regular")
        started = store.snapshot()["modes"]["regular"]["ongoing"]
        self.assertTrue(started["started_at"])
        self.assertTrue(started["tracking_started_at"])

    def test_version_one_early_start_is_reset_to_pending(self):
        learning_path = Path(self.temp_dir.name) / "learning.json"
        learning_path.write_text(json.dumps({
            "version": 1,
            "modes": {
                "regular": {
                    "history": [],
                    "ongoing": {
                        "round": 1,
                        "started_at": "2026-01-01T10:00:00+08:00",
                        "tracking_started_at": "2026-01-01T10:00:00+08:00",
                        "active_seconds": 999,
                        "total": 100,
                    },
                }
            },
            "wrong_rounds": {},
        }), encoding="utf-8")
        store = ChallengeLearningStore(str(learning_path))
        store.ensure_round(
            "regular", {"round": 1, "current": 1, "total": 100, "wrong": 0},
            started_before_tracking=False,
        )
        ongoing = store.snapshot()["modes"]["regular"]["ongoing"]
        self.assertIsNone(ongoing["started_at"])
        self.assertIsNone(ongoing["tracking_started_at"])
        self.assertEqual(ongoing["active_seconds"], 0)

    def test_wrong_round_count_deduplicates_same_round(self):
        learning_path = str(Path(self.temp_dir.name) / "learning.json")
        store = ChallengeLearningStore(learning_path)
        item = {"word": "apple", "content": "苹果"}
        store.record_wrong_round("regular", item, 2)
        store.record_wrong_round("regular", item, 2)
        store.record_wrong_round("regular", item, 5)
        record = store.wrong_round_record("regular", {"word": "apple"})
        self.assertEqual(record["count"], 2)
        self.assertEqual(record["last_round"], 5)
        self.assertEqual(
            store.wrong_round_text("regular", item),
            "错题轮次：累计2轮｜最近第5轮",
        )
        self.assertIn(
            "历史错词", store.wrong_round_text("regular", {"word": "old"}))

    def test_full_upgrade_backup_copies_existing_files_once(self):
        data_dir = Path(self.temp_dir.name)
        mistake = data_dir / "mistake_words.json"
        progress = data_dir / "challenge_round_progress.json"
        mistake.write_text('[{"word":"kept"}]', encoding="utf-8")
        progress.write_text('{"version":1}', encoding="utf-8")
        backup_dir = Path(backup_learning_upgrade_once(
            str(data_dir), [mistake.name, progress.name]))
        self.assertEqual(
            (backup_dir / mistake.name).read_text(encoding="utf-8"),
            '[{"word":"kept"}]',
        )
        mistake.write_text("[]", encoding="utf-8")
        self.assertEqual(
            Path(backup_learning_upgrade_once(
                str(data_dir), [mistake.name])).resolve(),
            backup_dir.resolve(),
        )


if __name__ == "__main__":
    unittest.main()
