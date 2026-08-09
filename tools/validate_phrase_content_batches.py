from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data_sources/clean/phrase_master_english/phrase_master_english.json"
BATCH_DIR = ROOT / "data_sources/enrichment/phrase_content_batches"
REPORT = BATCH_DIR / "validation_report.json"
FIELDS = [
    "record_id",
    "phrase",
    "meaning_zh",
    "usage_note_zh",
    "example_en",
    "example_zh",
    "content_method",
    "qa_status",
    "human_review_claimed",
]


def has_chinese(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", value))


def realizes_target_phrase(phrase: str, example: str) -> bool:
    """Accept exact forms plus a small audited set of separable structures."""
    folded_phrase = phrase.casefold()
    folded_example = example.casefold()
    if folded_phrase in folded_example:
        return True
    separable_patterns = {
        "regard as": r"\bregard\b(?:\s+\w+){1,6}\s+\bas\b",
        "tide over": r"\btide\b(?:\s+\w+){1,6}\s+\bover\b",
    }
    pattern = separable_patterns.get(folded_phrase)
    return bool(pattern and re.search(pattern, folded_example))


def main() -> int:
    master_rows = json.loads(MASTER.read_text(encoding="utf-8"))
    master = {row["record_id"]: row for row in master_rows}
    errors: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    seen_examples: dict[str, str] = {}
    rows_checked = 0

    batch_files = sorted(BATCH_DIR.glob("batch_*.tsv"))
    if not batch_files:
        errors.append("no batch_*.tsv files found")

    for path in batch_files:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames != FIELDS:
                errors.append(f"{path.name}: invalid fields: {reader.fieldnames}")
                continue
            for line_no, row in enumerate(reader, start=2):
                rows_checked += 1
                label = f"{path.name}:{line_no}"
                rid = row["record_id"].strip()
                if rid in seen_ids:
                    errors.append(f"{label}: duplicate record_id {rid}")
                seen_ids.add(rid)
                if rid not in master:
                    errors.append(f"{label}: record_id not in frozen master: {rid}")
                    continue
                if row["phrase"] != master[rid]["phrase"]:
                    errors.append(f"{label}: phrase differs from frozen master")
                for field in FIELDS:
                    if not row[field].strip():
                        errors.append(f"{label}: empty {field}")
                if not has_chinese(row["meaning_zh"]):
                    errors.append(f"{label}: meaning_zh has no Chinese")
                if not has_chinese(row["usage_note_zh"]):
                    errors.append(f"{label}: usage_note_zh has no Chinese")
                if not has_chinese(row["example_zh"]):
                    errors.append(f"{label}: example_zh has no Chinese")
                if "/" in row["phrase"] or "/" in row["example_en"]:
                    errors.append(f"{label}: slash found in English content")
                if not realizes_target_phrase(row["phrase"], row["example_en"]):
                    warnings.append(f"{label}: target phrase is not realized in example_en")
                normalized_example = re.sub(r"\s+", " ", row["example_en"].strip().casefold())
                if normalized_example in seen_examples:
                    errors.append(
                        f"{label}: duplicate English example; first used by {seen_examples[normalized_example]}"
                    )
                seen_examples[normalized_example] = rid
                if row["content_method"] != "original_project_authored":
                    errors.append(f"{label}: unexpected content_method")
                if row["qa_status"] != "draft_auto_validated":
                    errors.append(f"{label}: unexpected qa_status")
                if row["human_review_claimed"].strip().casefold() != "false":
                    errors.append(f"{label}: human_review_claimed must be false")

    master_counts = Counter(row["introduced_level"] for row in master_rows)
    covered_counts = Counter(master[rid]["introduced_level"] for rid in seen_ids if rid in master)
    missing_by_level = {
        level: sorted(
            row["record_id"]
            for row in master_rows
            if row["introduced_level"] == level and row["record_id"] not in seen_ids
        )
        for level in master_counts
    }
    report = {
        "rows_checked": rows_checked,
        "batch_files": [p.name for p in batch_files],
        "unique_record_ids": len(seen_ids),
        "coverage_by_level": {
            level: {
                "covered": covered_counts[level],
                "master_total": master_counts[level],
                "complete": covered_counts[level] == master_counts[level],
                "missing_count": len(missing_by_level[level]),
            }
            for level in master_counts
        },
        "errors": errors,
        "warnings": warnings,
        "passed": not errors,
        "human_review_claimed": False,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
