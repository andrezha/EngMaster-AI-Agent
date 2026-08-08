import json
import tempfile
from pathlib import Path

from utils import import_legacy_data_to_current_app


def test_import_legacy_data_keeps_only_unanswered_mistakes(tmp_path):
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    (source_dir / "mistake_words.json").write_text(
        json.dumps(
            [
                {"word": "keep", "content": "保留", "correct_count": 0},
                {"word": "remove", "content": "移除", "correct_count": 1},
                {"word": "missing", "content": "缺失"},
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (source_dir / "challenge_round_progress.json").write_text(
        json.dumps({"mode": "regular"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (source_dir / "challenge_learning_records.json").write_text(
        json.dumps({"records": [1, 2]}, ensure_ascii=False),
        encoding="utf-8",
    )

    summary = import_legacy_data_to_current_app(
        str(source_dir),
        str(target_dir),
        keep_only_unanswered=True,
    )

    imported_mistakes = json.loads(
        (target_dir / "mistake_words.json").read_text(encoding="utf-8")
    )
    assert [item["word"] for item in imported_mistakes] == ["keep", "missing"]
    assert summary["mistake_words.json"]["kept_count"] == 2
    assert (target_dir / "challenge_round_progress.json").exists()
    assert (target_dir / "challenge_learning_records.json").exists()
