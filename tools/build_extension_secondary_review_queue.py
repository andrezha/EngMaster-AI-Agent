"""Build the deduplicated secondary extension review queue."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data_sources/processed"
DEFAULT_OUTPUT = ROOT / "data_sources/clean/extension_secondary_review"

FIELDS = [
    "queue_id",
    "word",
    "legacy_candidate_form",
    "queue_route",
    "relevance_score",
    "bnc_rank",
    "contemporary_rank",
    "part_of_speech",
    "oewn_lexicographer_classes",
    "theme_candidates",
    "review_focus",
    "current_status",
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
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED)
    parser.add_argument("--curriculum", type=Path, default=ROOT / "data_sources/clean/curriculum_base.json")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    reasons = read_csv(args.processed_dir / "extension_inclusion_reason_candidates.csv")
    reason_by_word = {row["word"]: row for row in reasons}
    normalized = read_csv(args.processed_dir / "extension_normalized_new_headwords.csv")
    promoted = read_csv(args.processed_dir / "extension_hold_promoted_to_secondary.csv")
    form_resolutions = read_csv(args.processed_dir / "extension_form_resolution.csv")
    special_words = {
        row["legacy_word"]
        for row in form_resolutions
        if row["resolution"] == "move_to_special_reference_review"
    }

    queue: list[dict[str, object]] = []
    for row in reasons:
        if row["relevance_recommendation"] != "secondary_relevance_review":
            continue
        if row["word"] in special_words:
            continue
        queue.append(
            {
                "word": row["word"],
                "legacy_candidate_form": row["word"],
                "queue_route": "original_medium_frequency",
                "relevance_score": row["relevance_score"],
                "bnc_rank": row["bnc_rank"],
                "contemporary_rank": row["contemporary_rank"],
                "part_of_speech": row["oewn_pos"],
                "oewn_lexicographer_classes": row["oewn_lexicographer_classes"],
                "theme_candidates": row["theme_candidates"],
                "review_focus": "结合高中阅读主题、词族冗余和英美变体决定是否纳入",
            }
        )
    for row in normalized:
        if row["recommendation"] != "secondary_relevance_review":
            continue
        queue.append(
            {
                "word": row["word"],
                "legacy_candidate_form": row["replaces_legacy_form"],
                "queue_route": "normalized_legacy_surface_form",
                "relevance_score": row["relevance_score"],
                "bnc_rank": row["bnc_rank"],
                "contemporary_rank": row["contemporary_rank"],
                "part_of_speech": row["oewn_pos"],
                "oewn_lexicographer_classes": row["oewn_lexicographer_classes"],
                "theme_candidates": row["theme_candidates"],
                "review_focus": "确认规范词头的主题价值；不得恢复旧复数形式",
            }
        )
    for review in promoted:
        evidence = reason_by_word[review["word"]]
        queue.append(
            {
                "word": review["word"],
                "legacy_candidate_form": review["word"],
                "queue_route": "promoted_from_low_frequency_semantic_review",
                "relevance_score": review["relevance_score"],
                "bnc_rank": review["bnc_rank"],
                "contemporary_rank": review["contemporary_rank"],
                "part_of_speech": review["oewn_pos"],
                "oewn_lexicographer_classes": evidence["oewn_lexicographer_classes"],
                "theme_candidates": review["educational_theme"],
                "review_focus": review["decision_reason"],
            }
        )

    queue.sort(key=lambda row: str(row["word"]).casefold())
    words = [str(row["word"]) for row in queue]
    if len(words) != len({word.casefold() for word in words}):
        raise RuntimeError("Duplicate or case-colliding word in secondary queue")

    curriculum_data = json.loads(args.curriculum.read_text(encoding="utf-8"))
    curriculum_words = {
        form.casefold()
        for row in curriculum_data["records"]
        for form in [row["word"], *row.get("official_variants", [])]
    }
    overlap = sorted({word.casefold() for word in words} & curriculum_words)
    if overlap:
        raise RuntimeError(f"Secondary queue overlaps curriculum: {overlap[:10]}")

    for index, row in enumerate(queue, start=1):
        row.update(
            {
                "queue_id": f"secondary-review-{index:04d}",
                "current_status": "pending_explicit_semantic_decision",
                "definitions_zh": "",
                "phonetic_uk": "",
                "phonetic_us": "",
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "extension_secondary_review_queue.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(queue)

    json_path = args.output_dir / "extension_secondary_review_queue.json"
    json_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dataset_id": "engmaster-extension-secondary-review",
                "status": "pending_explicit_semantic_decision",
                "record_count": len(queue),
                "route_counts": Counter(str(row["queue_route"]) for row in queue),
                "records": queue,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    readme_path = args.output_dir / "README.md"
    route_counts = Counter(str(row["queue_route"]) for row in queue)
    readme_path.write_text(
        "# 扩展词二次复核队列\n\n"
        f"共 {len(queue)} 个唯一词头：原中档 {route_counts['original_medium_frequency']} 个，"
        f"规范化词头 {route_counts['normalized_legacy_surface_form']} 个，"
        f"从低频语义复核升入 {route_counts['promoted_from_low_frequency_semantic_review']} 个。\n\n"
        "本队列不代表最终收录；中文释义和音标字段均为空。\n",
        encoding="utf-8",
    )
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "dataset_id": "engmaster-extension-secondary-review",
                "record_count": len(queue),
                "route_counts": dict(route_counts),
                "curriculum_overlap_count": 0,
                "special_items_removed": sorted(special_words),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    written = [csv_path, json_path, readme_path, manifest_path]
    checksum_path = args.output_dir / "SHA256SUMS.txt"
    checksum_path.write_text(
        "\n".join(f"{sha256(path)}  {path.name}" for path in sorted(written)) + "\n",
        encoding="ascii",
    )
    print(f"Built {len(queue)} secondary-review records")
    print(dict(route_counts))


if __name__ == "__main__":
    main()
