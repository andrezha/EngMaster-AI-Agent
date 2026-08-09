#!/usr/bin/env python3
"""Build the 30-word high-school trial strictly from the release vocabulary."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/editions/gaokao/vocabulary.json"
OUTPUT = ROOT / "assets/editions/gaokao/trial_vocabulary.json"

TRIAL_WORDS = (
    "ability", "accept", "achieve", "active", "advantage", "advice",
    "affect", "allow", "although", "ancient", "appear", "attend", "avoid",
    "believe", "communicate", "compare", "complete", "consider", "continue",
    "culture", "develop", "environment", "experience", "improve", "knowledge",
    "opportunity", "possible", "protect", "provide", "responsibility",
)


def build_trial_vocabulary() -> list[dict[str, object]]:
    release_rows = json.loads(SOURCE.read_text(encoding="utf-8"))
    by_word: dict[str, list[dict[str, object]]] = {}
    for row in release_rows:
        by_word.setdefault(str(row.get("word", "")), []).append(row)

    selected: list[dict[str, object]] = []
    for word in TRIAL_WORDS:
        matches = by_word.get(word, [])
        if len(matches) != 1:
            raise ValueError(
                f"expected exactly one release row for {word!r}, found {len(matches)}"
            )
        selected.append(matches[0])
    return selected


def main() -> None:
    selected = build_trial_vocabulary()
    OUTPUT.write_text(
        json.dumps(selected, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"gaokao trial: {len(selected)} release rows -> {OUTPUT}")


if __name__ == "__main__":
    main()
