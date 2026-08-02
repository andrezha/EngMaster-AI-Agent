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

    def test_completed_irregular_round_reopens_as_round_two(self):
        first = ChallengeRoundStore(self.state_path, rng=random.Random(30))
        active = first.activate("irregular", self.items)
        while True:
            summary, active = first.advance("irregular", self.items)
            if summary:
                break

        self.assertEqual(summary["round"], 1)
        self.assertEqual(first.progress("irregular")["round"], 2)
        self.assertEqual(first.progress("irregular")["current"], 1)

        reopened = ChallengeRoundStore(self.state_path, rng=random.Random(31))
        reopened.activate("irregular", self.items)
        self.assertEqual(reopened.progress("irregular")["round"], 2)
        self.assertEqual(reopened.progress("irregular")["current"], 1)
        self.assertEqual(len(reopened.current_items("irregular")), len(self.items))

    def test_corrected_vocabulary_hash_alias_preserves_current_round(self):
        old_item = {"word": "performance", "content": "[pəˈfɔːm] n. 表演"}
        new_item = {"word": "performance", "content": "[pəˈfɔːməns] n. 表演"}
        other_item = {"word": "other", "content": "[ˈʌðə(r)] a. 其他的"}
        old_base = ChallengeRoundStore.item_base_key(old_item)
        new_base = ChallengeRoundStore.item_base_key(new_item)
        other_base = ChallengeRoundStore.item_base_key(other_item)
        Path(self.state_path).write_text(json.dumps({
            "version": 2,
            "modes": {
                "regular": {
                    "round": 2,
                    "completed": 5,
                    "remaining": [f"{old_base}:0", f"{other_base}:0"],
                    "wrong": [f"{old_base}:0"],
                    "retry_key": f"{old_base}:0",
                }
            },
        }, ensure_ascii=False), encoding="utf-8")

        restored = ChallengeRoundStore(
            self.state_path,
            key_aliases_by_mode={"regular": {old_base: new_base}},
        )
        active = restored.activate("regular", [new_item, other_item])

        self.assertEqual(active[0], new_item)
        self.assertEqual(len(active), 2)
        self.assertTrue(restored.is_retry_required("regular"))
        self.assertEqual(restored.progress("regular")["round"], 2)
        self.assertEqual(restored.progress("regular")["current"], 6)
        self.assertEqual(restored.progress("regular")["total"], 7)
        self.assertEqual(restored.progress("regular")["wrong"], 1)

    def test_irregular_wording_change_does_not_reset_round(self):
        old_items = [
            {"infinitive": "be", "past_tense": "was, were", "meaning": "是"},
            {"infinitive": "go", "past_tense": "went", "meaning": "去"},
        ]
        corrected_items = [
            {"infinitive": "be", "past_tense": "was, were", "meaning": "是；成为"},
            {"infinitive": "go", "past_tense": "went", "meaning": "去；前往"},
        ]
        first = ChallengeRoundStore(self.state_path, rng=random.Random(41))
        active = first.activate("irregular", old_items)
        completed_infinitive = active[0]["infinitive"]
        first.advance("irregular", old_items)

        restored = ChallengeRoundStore(self.state_path, rng=random.Random(42))
        active = restored.activate("irregular", corrected_items)
        self.assertEqual(restored.progress("irregular")["round"], 1)
        self.assertEqual(restored.progress("irregular")["current"], 2)
        self.assertEqual(len(active), 1)
        self.assertNotEqual(active[0]["infinitive"], completed_infinitive)

    def test_legacy_duplicate_words_remain_distinct_during_migration(self):
        noun = {"word": "break", "content": "n. 休息"}
        verb = {"word": "break", "content": "v. 打破"}
        noun_key = ChallengeRoundStore.item_base_key(noun)
        verb_key = ChallengeRoundStore.item_base_key(verb)
        Path(self.state_path).write_text(json.dumps({
            "version": 2,
            "modes": {
                "regular": {
                    "round": 2,
                    "completed": 7,
                    "remaining": [f"{noun_key}:0", f"{verb_key}:0"],
                    "wrong": [f"{verb_key}:0"],
                    "retry_key": None,
                }
            },
        }, ensure_ascii=False), encoding="utf-8")

        restored = ChallengeRoundStore(self.state_path)
        active = restored.activate("regular", [noun, verb])
        self.assertEqual(active, [noun, verb])
        self.assertEqual(restored.progress("regular")["round"], 2)
        self.assertEqual(restored.progress("regular")["current"], 8)
        self.assertEqual(restored.progress("regular")["total"], 9)
        self.assertEqual(restored.progress("regular")["wrong"], 1)

    def test_real_3800_word_progress_at_1000_survives_upgrade_and_reopen(self):
        root = Path(__file__).resolve().parent
        vocabulary = json.loads(
            (root / "assets" / "vocabulary.json").read_text(encoding="utf-8"))
        alias_data = json.loads(
            (root / "assets" / "vocabulary_progress_aliases.json").read_text(
                encoding="utf-8"))
        aliases = alias_data["regular"]
        reverse_aliases = {new: old for old, new in aliases.items()}
        legacy_occurrences = {}
        saved_keys = []
        for item in vocabulary:
            current_base = ChallengeRoundStore.item_base_key(item)
            saved_base = reverse_aliases.get(current_base, current_base)
            occurrence = legacy_occurrences.get(saved_base, 0)
            legacy_occurrences[saved_base] = occurrence + 1
            saved_keys.append(f"{saved_base}:{occurrence}")

        completed = 1000
        current_key = saved_keys[completed]
        wrong_keys = [saved_keys[20], saved_keys[500], current_key]
        Path(self.state_path).write_text(json.dumps({
            "version": 2,
            "modes": {
                "regular": {
                    "round": 1,
                    "completed": completed,
                    "remaining": saved_keys[completed:],
                    "wrong": wrong_keys,
                    "retry_key": current_key,
                }
            },
        }, ensure_ascii=False), encoding="utf-8")

        upgraded = ChallengeRoundStore(
            self.state_path, key_aliases_by_mode={"regular": aliases})
        active = upgraded.activate("regular", vocabulary)
        progress = upgraded.progress("regular")
        self.assertEqual(progress["round"], 1)
        self.assertEqual(progress["current"], 1001)
        self.assertEqual(progress["total"], len(vocabulary))
        self.assertEqual(progress["wrong"], 3)
        self.assertTrue(upgraded.is_retry_required("regular"))
        self.assertEqual(active, vocabulary[completed:])

        reopened = ChallengeRoundStore(
            self.state_path, key_aliases_by_mode={"regular": aliases})
        reopened_active = reopened.activate("regular", vocabulary)
        self.assertEqual(reopened.progress("regular"), progress)
        self.assertTrue(reopened.is_retry_required("regular"))
        self.assertEqual(reopened_active, active)

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

    def test_corrupt_primary_recovers_last_good_round_instead_of_round_one(self):
        first = ChallengeRoundStore(self.state_path, rng=random.Random(50))
        active = first.activate("irregular", self.items)
        while True:
            summary, active = first.advance("irregular", self.items)
            if summary:
                break
        self.assertEqual(first.progress("irregular")["round"], 2)
        Path(self.state_path).write_text("{broken", encoding="utf-8")

        recovered = ChallengeRoundStore(self.state_path, rng=random.Random(51))
        recovered.activate("irregular", self.items)
        self.assertTrue(recovered.recovered_from_backup)
        self.assertFalse(recovered.storage_error)
        self.assertEqual(recovered.progress("irregular")["round"], 2)

    def test_corrupt_primary_without_backup_is_never_silently_overwritten(self):
        original = b"{broken-progress"
        Path(self.state_path).write_bytes(original)
        store = ChallengeRoundStore(self.state_path, rng=random.Random(52))
        store.activate("irregular", self.items)

        self.assertTrue(store.storage_error)
        self.assertEqual(Path(self.state_path).read_bytes(), original)

    def test_backup_is_one_time_and_does_not_change_source(self):
        source = Path(self.temp_dir.name) / "mistake_words.json"
        source.write_text('[{"word":"kept"}]', encoding="utf-8")
        backup = Path(backup_existing_file_once(str(source)))
        source.write_text('[{"word":"new"}]', encoding="utf-8")
        backup_existing_file_once(str(source))

        self.assertEqual(backup.read_text(encoding="utf-8"), '[{"word":"kept"}]')
        self.assertEqual(source.read_text(encoding="utf-8"), '[{"word":"new"}]')

    def test_stable_identity_upgrade_keeps_original_progress_snapshot(self):
        original = json.dumps({
            "version": 2,
            "modes": {"irregular": {"round": 2, "completed": 0}},
        }, ensure_ascii=False).encode("utf-8")
        Path(self.state_path).write_bytes(original)

        ChallengeRoundStore(self.state_path)
        backups = list(Path(self.temp_dir.name).glob(
            "rounds.json.before_stable_identity_upgrade_*.bak"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)

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

    def test_learning_history_recovers_from_last_good_backup(self):
        learning_path = Path(self.temp_dir.name) / "learning.json"
        store = ChallengeLearningStore(str(learning_path))
        store.ensure_round(
            "irregular", {"round": 2, "current": 1, "total": 126, "wrong": 0})
        self.assertTrue(Path(f"{learning_path}.last_good.bak").is_file())
        learning_path.write_text("{broken-history", encoding="utf-8")

        recovered = ChallengeLearningStore(str(learning_path))
        snapshot = recovered.snapshot()
        self.assertTrue(recovered.recovered_from_backup)
        self.assertEqual(snapshot["modes"]["irregular"]["ongoing"]["round"], 2)

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
            "错词轮次：累计2轮｜最近第5轮",
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
