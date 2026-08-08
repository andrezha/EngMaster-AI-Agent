"""Build a clean, metadata-only draft of frequency-supported extension words."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data_sources/processed"
DEFAULT_REASONS = PROCESSED / "extension_inclusion_reason_candidates.csv"
DEFAULT_NORMALIZED = PROCESSED / "extension_normalized_new_headwords.csv"
DEFAULT_OUTPUT = ROOT / "data_sources/clean/extension_priority_draft"

FIELDS = [
    "record_id",
    "word",
    "legacy_candidate_form",
    "dataset_layer",
    "selection_status",
    "relevance_score",
    "bnc_rank",
    "contemporary_rank",
    "part_of_speech",
    "oewn_lexicographer_classes",
    "theme_candidates",
    "inclusion_reason",
    "selection_sources",
    "definitions_zh",
    "phonetic_uk",
    "phonetic_us",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reasons", type=Path, default=DEFAULT_REASONS)
    parser.add_argument("--normalized", type=Path, default=DEFAULT_NORMALIZED)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    reason_rows = [
        row
        for row in read_csv(args.reasons)
        if row["relevance_recommendation"] == "frequency_supported_extension"
    ]
    normalized_rows = [
        row
        for row in read_csv(args.normalized)
        if row["recommendation"] == "frequency_supported_extension"
    ]

    draft: list[dict[str, object]] = []
    for row in reason_rows:
        draft.append(
            {
                "word": row["word"],
                "legacy_candidate_form": row["word"],
                "relevance_score": int(row["relevance_score"]),
                "bnc_rank": row["bnc_rank"],
                "contemporary_rank": row["contemporary_rank"],
                "part_of_speech": row["oewn_pos"],
                "oewn_lexicographer_classes": row["oewn_lexicographer_classes"],
                "theme_candidates": row["theme_candidates"],
                "inclusion_reason": row["independent_inclusion_reason"],
            }
        )
    for row in normalized_rows:
        draft.append(
            {
                "word": row["word"],
                "legacy_candidate_form": row["replaces_legacy_form"],
                "relevance_score": int(row["relevance_score"]),
                "bnc_rank": row["bnc_rank"],
                "contemporary_rank": row["contemporary_rank"],
                "part_of_speech": row["oewn_pos"],
                "oewn_lexicographer_classes": row["oewn_lexicographer_classes"],
                "theme_candidates": row["theme_candidates"],
                "inclusion_reason": row["independent_inclusion_reason"],
            }
        )

    draft.sort(key=lambda row: str(row["word"]).casefold())
    words = [str(row["word"]) for row in draft]
    if len(words) != len(set(words)):
        raise RuntimeError("Duplicate word in extension priority draft")

    for index, row in enumerate(draft, start=1):
        row.update(
            {
                "record_id": f"extension-draft-{index:04d}",
                "dataset_layer": "extension",
                "selection_status": "draft_priority_needs_semantic_review",
                "selection_sources": "OEWN-2025-lexical-evidence|ECDICT-BNC-rank|ECDICT-contemporary-rank",
                "definitions_zh": "",
                "phonetic_uk": "",
                "phonetic_us": "",
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "extension_priority_draft.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(draft)

    json_path = args.output_dir / "extension_priority_draft.json"
    payload = {
        "schema_version": 1,
        "dataset_id": "engmaster-extension-priority-draft",
        "status": "draft_priority_needs_semantic_review",
        "record_count": len(draft),
        "selection_rule": "relevance_score >= 7; gk and other exam-list tags excluded from scoring",
        "content_policy": "Metadata only. Chinese definitions and phonetics intentionally blank.",
        "records": draft,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest_path = args.output_dir / "manifest.json"
    manifest = {
        "dataset_id": payload["dataset_id"],
        "status": payload["status"],
        "record_count": len(draft),
        "legacy_surface_forms_normalized": {
            row["legacy_candidate_form"]: row["word"]
            for row in draft
            if row["legacy_candidate_form"] != row["word"]
        },
        "excluded_scoring_fields": ["gk", "zk", "cet4", "oxford", "collins"],
        "forbidden_legacy_content": ["Chinese definitions", "phonetics", "examples", "legacy order"],
        "inputs": [args.reasons.as_posix(), args.normalized.as_posix()],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readme_path = args.output_dir / "README.md"
    readme_path.write_text(
        "# 扩展词优先候选草案\n\n"
        f"本目录包含 {len(draft)} 个频率证据较强的课标外候选词。它不是最终发布词库，所有记录仍需义项和主题复核。\n\n"
        "- 不使用 ECDICT 的 `gk` 等考试标签决定收录。\n"
        "- 不继承旧词库的释义、音标、例句、顺序或编号。\n"
        "- 中文释义和英美音标字段有意留空。\n"
        "- `souvenirs` 已规范为词头 `souvenir`。\n"
        "- 课标母表尚未与本草案合并。\n",
        encoding="utf-8",
    )

    written = [csv_path, json_path, manifest_path, readme_path]
    checksum_path = args.output_dir / "SHA256SUMS.txt"
    checksum_path.write_text(
        "\n".join(f"{sha256(path)}  {path.name}" for path in sorted(written)) + "\n",
        encoding="ascii",
    )
    print(f"Built {len(draft)} priority extension draft records in {args.output_dir}")


if __name__ == "__main__":
    main()
