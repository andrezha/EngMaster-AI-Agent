"""Build independent phrase/irregular-verb files for every EngMaster edition.

The current high-school phrase file remains the audited master source.  The
first preview keeps its existing order stable, marks 350 rows as core, 150 as
extension, and retains the remaining rows as hidden candidates.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "research" / "edition_samples"
PHRASE_MASTER = ROOT / "assets" / "short_phrase.json"
IRREGULAR_MASTER = ROOT / "assets" / "irregular_verbs.json"

FULL_EDITIONS = ("gaokao", "cet4", "cet6", "kaoyan")


def _read(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _decorate_phrases(edition_id: str, rows: list[dict], compact=False) -> list[dict]:
    result = []
    for index, original in enumerate(rows):
        item = dict(original)
        if compact:
            tier = "core"
            level = index // 50 + 1
        elif index < 350:
            tier = "core"
            level = index // 50 + 1
        elif index < 500:
            tier = "extension"
            level = (index - 350) // 50 + 1
        else:
            tier = "candidate"
            level = 0
        item["id"] = f"{edition_id}-phrase-{index + 1:03d}"
        item["tier"] = tier
        item["level"] = level
        result.append(item)
    return result


def _decorate_irregulars(edition_id: str, rows: list[dict]) -> list[dict]:
    result = []
    for index, original in enumerate(rows):
        item = dict(original)
        item["id"] = f"{edition_id}-irregular-{index + 1:03d}"
        item["level"] = index // 50 + 1
        result.append(item)
    return result


def main() -> None:
    phrase_master = _read(PHRASE_MASTER)
    irregular_master = _read(IRREGULAR_MASTER)
    for edition_id in FULL_EDITIONS:
        _write(
            SAMPLE_DIR / f"{edition_id}_phrases.json",
            _decorate_phrases(edition_id, phrase_master),
        )
        _write(
            SAMPLE_DIR / f"{edition_id}_irregular_verbs.json",
            _decorate_irregulars(edition_id, irregular_master),
        )

    junior_phrases = _read(SAMPLE_DIR / "zhongkao_phrases.json")
    junior_irregulars = _read(SAMPLE_DIR / "zhongkao_irregular_verbs.json")
    _write(
        SAMPLE_DIR / "zhongkao_phrases.json",
        _decorate_phrases("zhongkao", junior_phrases, compact=True),
    )
    _write(
        SAMPLE_DIR / "zhongkao_irregular_verbs.json",
        _decorate_irregulars("zhongkao", junior_irregulars),
    )


if __name__ == "__main__":
    main()
