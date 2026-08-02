#!/usr/bin/env python3
"""Build small, development-only edition samples from Qwerty Learner dictionaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SAMPLE_WORDS = {
    "zhongkao": [
        "classroom", "family", "parent", "subject", "homework", "library",
        "weather", "season", "healthy", "exercise", "breakfast", "vegetable",
        "hospital", "travel", "holiday", "museum", "country", "language",
        "future", "dream", "environment", "protect", "volunteer", "culture",
        "festival", "traffic", "important", "different", "because", "together",
    ],
    "cet4": [
        "academic", "campus", "assignment", "deadline", "graduate", "employment",
        "interview", "technology", "environment", "consume", "resource",
        "efficient", "benefit", "challenge", "communicate", "community",
        "culture", "economy", "evidence", "factor", "individual", "maintain",
        "opportunity", "participate", "professional", "respond", "significant",
        "strategy", "transport", "volunteer",
    ],
    "cet6": [
        "ambiguous", "coherent", "comprehensive", "controversial", "crucial",
        "deteriorate", "dilemma", "empirical", "enhance", "explicit", "feasible",
        "fluctuate", "fundamental", "hypothesis", "inevitable", "interpret",
        "intricate", "manipulate", "obscure", "paradox", "persistent",
        "plausible", "preliminary", "profound", "reinforce", "sophisticated",
        "substantial", "consecutive", "allocate", "contradiction",
    ],
    "kaoyan": [
        "analysis", "approach", "assume", "concept", "context", "define",
        "derive", "establish", "evidence", "factor", "indicate", "interpret",
        "involve", "issue", "method", "occur", "principle", "process",
        "require", "research", "significant", "hypothesis", "vary", "available",
        "benefit", "challenge", "environment", "individual", "maintain",
        "respond",
    ],
}

SOURCE_FILES = {
    "zhongkao": "ZhongKaoHeXin.json",
    "cet4": "CET4_T.json",
    "cet6": "CET6_T.json",
    "kaoyan": "KaoYan_2024.json",
}


def _translations(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def build_sample(source_dir: Path, edition: str) -> list[dict]:
    source_name = SOURCE_FILES[edition]
    source_path = source_dir / source_name
    rows = json.loads(source_path.read_text(encoding="utf-8"))
    by_word = {
        str(row.get("name", "")).strip().lower(): row
        for row in rows
        if str(row.get("name", "")).strip()
    }

    result = []
    missing = []
    for requested_word in SAMPLE_WORDS[edition]:
        row = by_word.get(requested_word)
        if row is None:
            missing.append(requested_word)
            continue

        word = str(row["name"]).strip()
        pronunciation = str(row.get("usphone") or row.get("ukphone") or "").strip()
        meaning = "；".join(_translations(row.get("trans")))
        content = f"[{pronunciation}] {meaning}" if pronunciation else meaning
        result.append(
            {
                "id": f"{edition}:{word.lower()}",
                "word": word,
                "pronunciation": pronunciation,
                "content": content,
                "edition": edition,
                "source": source_name,
                "data_status": "development_sample",
            }
        )

    if missing:
        raise ValueError(f"{source_name} is missing selected words: {', '.join(missing)}")
    if len(result) != 30:
        raise ValueError(f"{edition} sample contains {len(result)} rows instead of 30")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path, help="Qwerty Learner public/dicts directory")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research/edition_samples"),
        help="Development sample output directory",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for edition in SOURCE_FILES:
        sample = build_sample(args.source_dir, edition)
        output_path = args.output_dir / f"{edition}_sample.json"
        output_path.write_text(
            json.dumps(sample, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"{edition}: {len(sample)} words -> {output_path}")


if __name__ == "__main__":
    main()
