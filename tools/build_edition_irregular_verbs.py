#!/usr/bin/env python3
"""Build development-only edition irregular-verb subsets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ZHONGKAO_VOCABULARY_SOURCES = (
    "ZhongKaoHeXin.json",
    "OxfordVocabulary_juniorMiddleSH.json",
)
ZHONGKAO_EXCLUDED_IRREGULARS = {
    "burst",
    "deal",
    "dream",
    "hang",
    "lay",
    "light",
    "mistake",
    "rise",
    "shine",
    "smell",
    "spread",
    "steal",
    "swing",
    "upset",
}


def build_zhongkao_irregulars(source_dir: Path, master_path: Path) -> list[dict]:
    vocabulary = set()
    for source_name in ZHONGKAO_VOCABULARY_SOURCES:
        rows = json.loads((source_dir / source_name).read_text(encoding="utf-8"))
        vocabulary.update(
            str(row.get("name", "")).strip().lower()
            for row in rows
            if str(row.get("name", "")).strip()
        )

    master_rows = json.loads(master_path.read_text(encoding="utf-8"))
    return [
        {
            **row,
            "edition": "zhongkao",
            "source": list(ZHONGKAO_VOCABULARY_SOURCES),
            "data_status": "development_candidate",
        }
        for row in master_rows
        if (
            str(row.get("infinitive", "")).strip().lower() in vocabulary
            and str(row.get("infinitive", "")).strip().lower()
            not in ZHONGKAO_EXCLUDED_IRREGULARS
        )
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument(
        "--master",
        type=Path,
        default=Path("assets/irregular_verbs.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/edition_samples/zhongkao_irregular_verbs.json"),
    )
    args = parser.parse_args()

    rows = build_zhongkao_irregulars(args.source_dir, args.master)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"zhongkao: {len(rows)} irregular verbs -> {args.output}")


if __name__ == "__main__":
    main()
