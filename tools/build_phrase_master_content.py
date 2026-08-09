"""Merge the frozen English phrase master with original Chinese content batches."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGLISH_MASTER = ROOT / "data_sources/clean/phrase_master_english/phrase_master_english.json"
BATCH_DIR = ROOT / "data_sources/enrichment/phrase_content_batches"
OUTPUT_DIR = ROOT / "data_sources/clean/phrase_master_content"
LEVELS = ("junior", "senior_high", "cet4", "cet6")
VIEW_NAMES = {
    "junior": "junior_phrases_250",
    "senior_high": "senior_high_phrases_450",
    "cet4": "cet4_phrases_750",
    "cet6": "cet6_phrases_1050",
}
CONTENT_FIELDS = (
    "meaning_zh",
    "usage_note_zh",
    "example_en",
    "example_zh",
    "content_method",
    "qa_status",
    "human_review_claimed",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_content_batches() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for path in sorted(BATCH_DIR.glob("batch_*.tsv")):
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream, delimiter="\t"):
                record_id = row["record_id"]
                if record_id in rows:
                    raise ValueError(f"duplicate content record: {record_id}")
                rows[record_id] = row
    return rows


def json_value(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return json.loads(stripped)
    if stripped.casefold() == "true":
        return True
    if stripped.casefold() == "false":
        return False
    return value


def csv_value(value: object) -> object:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


def write_dataset(stem: str, rows: list[dict[str, object]]) -> list[Path]:
    json_path = OUTPUT_DIR / f"{stem}.json"
    csv_path = OUTPUT_DIR / f"{stem}.csv"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({key: csv_value(value) for key, value in row.items()} for row in rows)
    return [json_path, csv_path]


def main() -> int:
    english_rows = json.loads(ENGLISH_MASTER.read_text(encoding="utf-8"))
    content = read_content_batches()
    english_ids = {row["record_id"] for row in english_rows}
    if english_ids != set(content):
        missing = sorted(english_ids - set(content))
        extra = sorted(set(content) - english_ids)
        raise ValueError(f"content/master mismatch; missing={missing}, extra={extra}")

    merged: list[dict[str, object]] = []
    for english in english_rows:
        item = {key: json_value(value) for key, value in english.items()}
        detail = content[english["record_id"]]
        if detail["phrase"] != english["phrase"]:
            raise ValueError(f"phrase mismatch for {english['record_id']}")
        item["meaning_zh"] = detail["meaning_zh"]
        item["usage_note_zh"] = detail["usage_note_zh"]
        item["example_en"] = detail["example_en"]
        item["example_zh"] = detail["example_zh"]
        item["content_method"] = detail["content_method"]
        item["content_qa_status"] = detail["qa_status"]
        item["human_review_claimed"] = False
        merged.append(item)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    primary_files = write_dataset("phrase_master_content_1050", merged)
    view_counts: dict[str, int] = {}
    for target_level in LEVELS:
        rows = [row for row in merged if target_level in row["included_in"]]
        for sequence, row in enumerate(rows, start=1):
            row["view_sequence"] = sequence
        primary_files.extend(write_dataset(VIEW_NAMES[target_level], rows))
        for row in rows:
            row.pop("view_sequence")
        view_counts[target_level] = len(rows)

    file_hashes = {path.name: sha256_file(path) for path in primary_files}
    manifest = {
        "status": "complete",
        "source_english_master": str(ENGLISH_MASTER.relative_to(ROOT)).replace("\\", "/"),
        "source_content_batches": [
            str(path.relative_to(ROOT)).replace("\\", "/")
            for path in sorted(BATCH_DIR.glob("batch_*.tsv"))
        ],
        "master_record_count": len(merged),
        "cumulative_view_counts": view_counts,
        "old_phrase_file_read": False,
        "human_review_claimed": False,
        "content_method": "original_project_authored",
        "file_sha256": file_hashes,
    }
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checksum_rows = [f"{digest}  {name}" for name, digest in sorted(file_hashes.items())]
    checksum_rows.append(f"{sha256_file(manifest_path)}  {manifest_path.name}")
    (OUTPUT_DIR / "SHA256SUMS.txt").write_text("\n".join(checksum_rows) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

