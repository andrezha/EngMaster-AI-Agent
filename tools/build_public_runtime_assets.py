"""Build the minimal, public runtime asset set used by commercial packages.

Canonical release files keep internal QA/provenance fields for maintainers.
The packaged copies contain only fields the application needs at runtime plus
the notices that must accompany redistributed third-party material.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets"
TARGET = ROOT / "packaging" / "public_assets"
EDITION_IDS = ("zhongkao", "gaokao")

VOCABULARY_FIELDS = (
    "word", "content", "record_id", "variants", "accepted_answers",
    "pronunciation",
)
PHRASE_FIELDS = (
    "id", "p", "m", "en", "cn", "answers", "tier", "level",
    "usage_note",
)
IRREGULAR_FIELDS = (
    "infinitive", "past_tense", "past_participle", "meaning",
    "accepted_past_tense", "accepted_past_participle",
)
PUBLIC_LICENSE_FILES = (
    "OPEN_ENGLISH_WORDNET_LICENSE.md",
    "PRINCETON_WORDNET_LICENSE.txt",
    "IPA_DICT_LICENSE.txt",
)


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _public_rows(source_edition: Path, target_edition: Path,
                 filename: str, fields: tuple[str, ...]) -> None:
    rows = _load_json(source_edition / filename)
    public_rows = [
        {field: row[field] for field in fields if field in row}
        for row in rows
    ]
    _write_json(target_edition / filename, public_rows)


def build() -> Path:
    for edition_id in EDITION_IDS:
        source_edition = SOURCE / "editions" / edition_id
        target_edition = TARGET / "editions" / edition_id
        target_edition.mkdir(parents=True, exist_ok=True)
        _public_rows(source_edition, target_edition, "vocabulary.json", VOCABULARY_FIELDS)
        _public_rows(source_edition, target_edition, "trial_vocabulary.json", VOCABULARY_FIELDS)
        _public_rows(source_edition, target_edition, "phrases.json", PHRASE_FIELDS)
        _public_rows(source_edition, target_edition, "irregular_verbs.json", IRREGULAR_FIELDS)
        shutil.copy2(
            source_edition / "scientific_memory_data.json",
            target_edition / "scientific_memory_data.json",
        )
        for filename in PUBLIC_LICENSE_FILES:
            shutil.copy2(source_edition / filename, target_edition / filename)
    return TARGET


if __name__ == "__main__":
    print(build())
