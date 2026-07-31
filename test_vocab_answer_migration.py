import json
import tempfile
import unittest
from pathlib import Path

from challenge_rounds import ChallengeRoundStore
from vocab_module import (
    LEGACY_ANSWER_RECORD_CONTENTS,
    LEGACY_ANSWER_RECORD_MIGRATIONS,
    _migrate_legacy_answer_data,
)


def _identity_key(word):
    return ChallengeRoundStore._identity_key({"word": word}) + ":0"


def test_legacy_answer_rows_and_learning_progress_are_migrated_once(tmp_path):
    old_words = list(LEGACY_ANSWER_RECORD_MIGRATIONS)
    old_records = [
        {
            "word": word,
            "content": LEGACY_ANSWER_RECORD_CONTENTS[word],
            "correct_count": index % 3,
        }
        for index, word in enumerate(old_words)
    ]
    pole_word = "the North (South) Pole"
    old_keys = [_identity_key(word) for word in old_words]

    mistake_path = tmp_path / "mistake_words.json"
    round_path = tmp_path / "challenge_round_progress.json"
    learning_path = tmp_path / "challenge_learning_records.json"
    mistake_path.write_text(
        json.dumps(old_records, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    round_path.write_text(
        json.dumps(
            {
                "version": 3,
                "modes": {
                    "regular": {
                        "round": 2,
                        "completed": 3869,
                        "remaining": old_keys,
                        "wrong": [_identity_key(pole_word)],
                        "retry_key": _identity_key(pole_word),
                    },
                    "mistake_list": {
                        "round": 1,
                        "completed": 0,
                        "remaining": old_keys,
                        "wrong": [_identity_key(pole_word)],
                        "retry_key": _identity_key(pole_word),
                    },
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    learning_path.write_text(
        json.dumps(
            {
                "wrong_rounds": {
                    "regular": {
                        f"word:{word.casefold()}": {
                            "count": 2,
                            "last_round": 3,
                        }
                        for word in old_words
                    },
                    "mistake_list": {
                        f"word:{pole_word.casefold()}": {
                            "count": 1,
                            "last_round": 1,
                        }
                    },
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    migrated = _migrate_legacy_answer_data(str(tmp_path))
    assert migrated is not None
    assert len(migrated) == 7
    migrated_by_word = {row["word"]: row for row in migrated}
    assert not set(old_words).intersection(migrated_by_word)
    assert migrated_by_word["afterward"]["accepted_answers"] == [
        "afterward",
        "afterwards",
    ]
    assert migrated_by_word["the North Pole"]["correct_count"] == 1
    assert migrated_by_word["the South Pole"]["correct_count"] == 1

    progress = json.loads(round_path.read_text(encoding="utf-8"))
    regular = progress["modes"]["regular"]
    mistake_list = progress["modes"]["mistake_list"]
    assert regular["completed"] + len(regular["remaining"]) == 3876
    assert len(regular["remaining"]) == 7
    assert len(mistake_list["remaining"]) == 7
    assert regular["retry_key"] == _identity_key("the North Pole")
    assert regular["wrong"] == [
        _identity_key("the North Pole"),
        _identity_key("the South Pole"),
    ]

    learning = json.loads(learning_path.read_text(encoding="utf-8"))
    regular_records = learning["wrong_rounds"]["regular"]
    assert f"word:{pole_word.casefold()}" not in regular_records
    assert regular_records["word:the north pole"]["last_round"] == 3
    assert regular_records["word:the south pole"]["count"] == 2
    mistake_records = learning["wrong_rounds"]["mistake_list"]
    assert "word:the north pole" in mistake_records
    assert "word:the south pole" in mistake_records

    assert list(tmp_path.glob(
        "mistake_words.json.before_answer_variants_migration_*.bak"))
    assert list(tmp_path.glob(
        "challenge_round_progress.json.before_answer_variants_migration_*.bak"))
    assert list(tmp_path.glob(
        "challenge_learning_records.json.before_answer_variants_migration_*.bak"))

    bytes_after_first_run = {
        path: path.read_bytes()
        for path in (mistake_path, round_path, learning_path)
    }
    assert _migrate_legacy_answer_data(str(tmp_path)) is None
    assert {
        path: path.read_bytes()
        for path in (mistake_path, round_path, learning_path)
    } == bytes_after_first_run


def test_regular_progress_migrates_without_a_mistake_file(tmp_path):
    pole_word = "the North (South) Pole"
    round_path = Path(tmp_path) / "challenge_round_progress.json"
    round_path.write_text(
        json.dumps(
            {
                "version": 3,
                "modes": {
                    "regular": {
                        "round": 1,
                        "completed": 3874,
                        "remaining": [_identity_key(pole_word)],
                        "wrong": [],
                        "retry_key": None,
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert _migrate_legacy_answer_data(str(tmp_path)) is None
    progress = json.loads(round_path.read_text(encoding="utf-8"))
    state = progress["modes"]["regular"]
    assert state["completed"] == 3874
    assert state["remaining"] == [
        _identity_key("the North Pole"),
        _identity_key("the South Pole"),
    ]
    assert state["completed"] + len(state["remaining"]) == 3876


class VocabAnswerMigrationTests(unittest.TestCase):
    def test_rows_and_progress_are_migrated_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_legacy_answer_rows_and_learning_progress_are_migrated_once(
                Path(temp_dir)
            )

    def test_regular_progress_without_mistake_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            test_regular_progress_migrates_without_a_mistake_file(
                Path(temp_dir)
            )
