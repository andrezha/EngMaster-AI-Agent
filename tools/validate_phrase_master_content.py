"""Validate merged phrase content and all cumulative product views."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data_sources/clean/phrase_master_content"
MANIFEST = DATA_DIR / "manifest.json"
REPORT = DATA_DIR / "validation_report.json"
VIEWS = {
    "junior": ("junior_phrases_250", 250),
    "senior_high": ("senior_high_phrases_450", 450),
    "cet4": ("cet4_phrases_750", 750),
    "cet6": ("cet6_phrases_1050", 1050),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_csv_row(row: dict[str, str], model: dict[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, expected in model.items():
        value = row[key]
        if isinstance(expected, bool):
            normalized[key] = value.casefold() == "true"
        elif isinstance(expected, int):
            normalized[key] = int(value)
        elif isinstance(expected, list):
            normalized[key] = json.loads(value)
        else:
            normalized[key] = value
    return normalized


def load_pair(stem: str, errors: list[str]) -> list[dict[str, object]]:
    json_path = DATA_DIR / f"{stem}.json"
    csv_path = DATA_DIR / f"{stem}.csv"
    json_rows = json.loads(json_path.read_text(encoding="utf-8"))
    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        raw_csv_rows = list(csv.DictReader(stream))
    if len(json_rows) != len(raw_csv_rows):
        errors.append(f"{stem}: JSON/CSV row counts differ")
        return json_rows
    for index, (json_row, csv_row) in enumerate(zip(json_rows, raw_csv_rows), start=1):
        if list(json_row) != list(csv_row):
            errors.append(f"{stem}:{index}: JSON/CSV fields differ")
            continue
        if json_row != normalize_csv_row(csv_row, json_row):
            errors.append(f"{stem}:{index}: JSON/CSV values differ")
    return json_rows


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for name, expected_hash in manifest["file_sha256"].items():
        path = DATA_DIR / name
        if not path.exists():
            errors.append(f"missing hashed file: {name}")
        elif sha256_file(path) != expected_hash:
            errors.append(f"hash mismatch: {name}")

    master = load_pair("phrase_master_content_1050", errors)
    master_ids = [row["record_id"] for row in master]
    if len(master) != 1050:
        errors.append(f"master expected 1050 rows, found {len(master)}")
    if len(set(master_ids)) != len(master_ids):
        errors.append("duplicate record_id in master")
    normalized_phrases = [re.sub(r"\s+", " ", row["phrase"].strip().casefold()) for row in master]
    if len(set(normalized_phrases)) != len(normalized_phrases):
        errors.append("duplicate normalized phrase in master")

    examples: set[str] = set()
    required_text = ("phrase", "meaning_zh", "usage_note_zh", "example_en", "example_zh")
    for row in master:
        record_id = row["record_id"]
        for field in required_text:
            if not str(row[field]).strip():
                errors.append(f"{record_id}: empty {field}")
        if not re.search(r"[\u3400-\u9fff]", row["meaning_zh"]):
            errors.append(f"{record_id}: meaning_zh has no Chinese")
        if "/" in row["phrase"] or "/" in row["example_en"]:
            errors.append(f"{record_id}: slash in English learning content")
        example_key = re.sub(r"\s+", " ", row["example_en"].strip().casefold())
        if example_key in examples:
            errors.append(f"{record_id}: duplicate English example")
        examples.add(example_key)
        if row["content_method"] != "original_project_authored":
            errors.append(f"{record_id}: unexpected content_method")
        if row["content_qa_status"] != "draft_auto_validated":
            errors.append(f"{record_id}: unexpected content_qa_status")
        if row["human_review_claimed"] is not False:
            errors.append(f"{record_id}: human_review_claimed must be false")

    master_by_id = {row["record_id"]: row for row in master}
    view_counts: dict[str, int] = {}
    for level, (stem, expected_count) in VIEWS.items():
        view = load_pair(stem, errors)
        view_counts[level] = len(view)
        expected_ids = [row["record_id"] for row in master if level in row["included_in"]]
        actual_ids = [row["record_id"] for row in view]
        if len(view) != expected_count:
            errors.append(f"{level}: expected {expected_count} rows, found {len(view)}")
        if actual_ids != expected_ids:
            errors.append(f"{level}: membership or order differs from master")
        if [row["view_sequence"] for row in view] != list(range(1, len(view) + 1)):
            errors.append(f"{level}: invalid view_sequence")
        for row in view:
            base = dict(row)
            base.pop("view_sequence")
            if base != master_by_id.get(row["record_id"]):
                errors.append(f"{level}:{row['record_id']}: content differs from master")

    if manifest.get("old_phrase_file_read") is not False:
        errors.append("manifest must record old_phrase_file_read=false")
    if manifest.get("human_review_claimed") is not False:
        errors.append("manifest must record human_review_claimed=false")

    report = {
        "status": "pass" if not errors else "fail",
        "master_record_count": len(master),
        "cumulative_view_counts": view_counts,
        "unique_record_ids": len(set(master_ids)),
        "unique_normalized_phrases": len(set(normalized_phrases)),
        "unique_english_examples": len(examples),
        "hashes_verified": len(manifest.get("file_sha256", {})),
        "errors": errors,
        "warnings": warnings,
        "old_phrase_file_read": False,
        "human_review_claimed": False,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

