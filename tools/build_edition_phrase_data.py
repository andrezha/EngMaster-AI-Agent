#!/usr/bin/env python3
"""Build development-only edition phrase data from external dictionary JSON."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ZHONGKAO_SOURCE = "OxfordVocabulary_juniorMiddleSH.json"
ZHONGKAO_NAME_FIXES = {
    "take partin": "take part in",
    "bekeen on": "be keen on",
    "sot hat": "so that",
    "and soon": "and so on",
    "the green house effect": "the greenhouse effect",
    "jump to conclusion": "jump to a conclusion",
}
ZHONGKAO_EXCLUDED_PHRASES = {
    "at the end of August",
    "hold out",
    "be going on",
    "go after",
    "in a flash",
    "like lightning",
    "bring down",
    "in pieces",
    "be done for",
    "take charge of",
    "agree on",
    "save one's life",
    "clean out",
    "make a complaint",
    "be unaware of",
    "common knowledge",
    "link method",
    "the Olympic Games",
    "jump to a conclusion",
    "behind bars",
    "come to life",
    "burst out (doing)",
    "get a view of",
    "ahead of",
    "set out",
    "ballroom dancing",
    "be amazed at",
    "pay a visit",
    "have the time of one's life",
    "jump out of one's skin",
    "cut a long story short",
    "green with envy",
    "trick...into doing sth",
}


def _normalize_phrase(value: str) -> str:
    text = str(value or "").strip().lower().replace("(be)", "be")
    text = text.replace("...", " ")
    return re.sub(r"[^a-z]+", " ", text).strip()


def _clean_phrase_name(value: str) -> str:
    text = str(value or "").strip()
    text = ZHONGKAO_NAME_FIXES.get(text, text)
    text = text.replace("(be)", "be")
    return re.sub(r"\s+", " ", text).strip()


def _clean_meaning(values) -> str:
    if not isinstance(values, list):
        values = [values]
    meaning = "；".join(str(value).strip() for value in values if str(value).strip())
    return re.sub(r"^n(?=[\u4e00-\u9fff])", "", meaning).strip()


def build_zhongkao_phrases(source_dir: Path, existing_phrase_path: Path) -> list[dict]:
    source_path = source_dir / ZHONGKAO_SOURCE
    source_rows = json.loads(source_path.read_text(encoding="utf-8"))
    existing_rows = json.loads(existing_phrase_path.read_text(encoding="utf-8"))
    existing_by_phrase = {
        _normalize_phrase(row.get("p", "")): row
        for row in existing_rows
        if _normalize_phrase(row.get("p", ""))
    }

    result = []
    seen = set()
    for row in source_rows:
        raw_name = str(row.get("name", "")).strip()
        if len(raw_name.split()) <= 1:
            continue

        phrase = _clean_phrase_name(raw_name)
        phrase_key = _normalize_phrase(phrase)
        if (
            not phrase_key
            or phrase_key in seen
            or phrase in ZHONGKAO_EXCLUDED_PHRASES
        ):
            continue
        seen.add(phrase_key)

        existing = existing_by_phrase.get(phrase_key, {})
        result.append(
            {
                "id": f"zhongkao_phrase:{len(result) + 1:03d}",
                "p": phrase,
                "m": _clean_meaning(row.get("trans", [])),
                "en": str(existing.get("en", "")).strip(),
                "cn": str(existing.get("cn", "")).strip(),
                "answers": [phrase],
                "edition": "zhongkao",
                "source": ZHONGKAO_SOURCE,
                "data_status": "development_candidate",
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument(
        "--existing-phrases",
        type=Path,
        default=Path("assets/short_phrase.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/edition_samples/zhongkao_phrases.json"),
    )
    args = parser.parse_args()

    rows = build_zhongkao_phrases(args.source_dir, args.existing_phrases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with_examples = sum(bool(row["en"] and row["cn"]) for row in rows)
    print(f"zhongkao: {len(rows)} phrases, {with_examples} with examples -> {args.output}")


if __name__ == "__main__":
    main()
