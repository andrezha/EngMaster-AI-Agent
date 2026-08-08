"""Build the clean curriculum vocabulary base from the MOE master table.

The generated base contains no legacy definitions or phonetics. Four official
entries containing ``/`` are split into atomic learning records while retaining
their shared official source sequence.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data_sources" / "processed" / "curriculum_vocabulary.json"
OUTPUT_DIR = ROOT / "data_sources" / "clean"
JSON_PATH = OUTPUT_DIR / "curriculum_base.json"
CSV_PATH = OUTPUT_DIR / "curriculum_base.csv"
MANIFEST_PATH = OUTPUT_DIR / "curriculum_base_manifest.json"
HASH_PATH = OUTPUT_DIR / "SHA256SUMS.txt"

SCHEMA_VERSION = 1
EXPECTED_SOURCE_ENTRIES = 3000
EXPECTED_SLASH_ENTRIES = 4
EXPECTED_ATOMIC_RECORDS = 3004


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compact(value: str) -> str:
    return " ".join(value.strip().split())


def official_variants(headword: str, note: str) -> list[str]:
    note = compact(note)
    if not note:
        return []
    if note == "s":
        return [headword + "s"]
    if note.casefold().startswith("pl. "):
        note = note[4:].strip()

    variants: list[str] = []
    for value in re.split(r"\s*[,/]\s*", note):
        value = compact(value.strip(" ,"))
        if value and value not in variants and value != headword:
            variants.append(value)
    return variants


def build_records(source_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    for source in source_rows:
        sequence = int(source["sequence"])
        headword = compact(str(source["headword"]))
        if "/" in headword:
            components = [compact(value) for value in headword.split("/")]
        else:
            components = [headword]

        variants = official_variants(
            headword, str(source.get("parenthetical_note", ""))
        )
        for component_index, word in enumerate(components, start=1):
            suffix = "" if len(components) == 1 else f"-{component_index}"
            records.append(
                {
                    "record_id": f"curriculum-{sequence:04d}{suffix}",
                    "word": word,
                    "official_variants": variants if len(components) == 1 else [],
                    "source_entry": str(source["entry"]),
                    "source_sequence": sequence,
                    "source_component_index": component_index,
                    "source_component_count": len(components),
                    "curriculum_level": str(source["curriculum_level"]),
                    "marker": str(source["marker"]),
                    "alphabetic_section": str(source["alphabetic_section"]),
                    "source_print_page": int(source["source_print_page"]),
                    "source_id": str(source["source_id"]),
                    "part_of_speech": [],
                    "definitions_zh": [],
                    "phonetic_uk": [],
                    "phonetic_us": [],
                    "enrichment_status": "pending_definition_and_phonetics",
                }
            )

    return records


def validate(
    source_rows: list[dict[str, object]], records: list[dict[str, object]]
) -> dict[str, object]:
    errors: list[str] = []
    slash_sources = [row for row in source_rows if "/" in str(row["headword"])]
    source_sequences = {int(row["sequence"]) for row in source_rows}
    record_sequences = {int(row["source_sequence"]) for row in records}

    if len(source_rows) != EXPECTED_SOURCE_ENTRIES:
        errors.append(
            f"expected {EXPECTED_SOURCE_ENTRIES} source entries, got {len(source_rows)}"
        )
    if len(slash_sources) != EXPECTED_SLASH_ENTRIES:
        errors.append(
            f"expected {EXPECTED_SLASH_ENTRIES} slash entries, got {len(slash_sources)}"
        )
    if len(records) != EXPECTED_ATOMIC_RECORDS:
        errors.append(
            f"expected {EXPECTED_ATOMIC_RECORDS} atomic records, got {len(records)}"
        )
    if source_sequences != record_sequences:
        errors.append("source sequence coverage is not one-to-one complete")

    record_ids = [str(row["record_id"]) for row in records]
    if len(record_ids) != len(set(record_ids)):
        errors.append("duplicate record_id values found")

    words = [str(row["word"]) for row in records]
    if len(words) != len(set(words)):
        duplicates = sorted(word for word, count in Counter(words).items() if count > 1)
        errors.append(f"duplicate exact atomic words found: {duplicates}")
    if any("/" in word for word in words):
        errors.append("slash remains in an atomic word field")
    if any("(" in word or ")" in word for word in words):
        errors.append("parenthetical annotation remains in an atomic word field")
    if any(
        row["part_of_speech"]
        or row["definitions_zh"]
        or row["phonetic_uk"]
        or row["phonetic_us"]
        for row in records
    ):
        errors.append("enrichment fields must be empty in the clean base")

    source_record_counts = Counter(int(row["source_sequence"]) for row in records)
    unexpected_multiplicity = {
        sequence: count
        for sequence, count in source_record_counts.items()
        if count not in {1, 2}
    }
    if unexpected_multiplicity:
        errors.append(f"unexpected source multiplicity: {unexpected_multiplicity}")

    split_sequences = sorted(
        sequence for sequence, count in source_record_counts.items() if count == 2
    )
    expected_split_sequences = sorted(int(row["sequence"]) for row in slash_sources)
    if split_sequences != expected_split_sequences:
        errors.append(
            f"split sequence mismatch: {split_sequences} != {expected_split_sequences}"
        )

    return {
        "valid": not errors,
        "errors": errors,
        "source_entry_count": len(source_rows),
        "atomic_record_count": len(records),
        "slash_source_entry_count": len(slash_sources),
        "split_source_sequences": split_sequences,
        "level_source_counts": dict(
            Counter(str(row["curriculum_level"]) for row in source_rows)
        ),
        "level_atomic_counts": dict(
            Counter(str(row["curriculum_level"]) for row in records)
        ),
        "record_status_counts": dict(
            Counter(str(row["enrichment_status"]) for row in records)
        ),
    }


def write_csv(records: list[dict[str, object]]) -> None:
    fieldnames = [
        "record_id",
        "word",
        "official_variants",
        "source_entry",
        "source_sequence",
        "source_component_index",
        "source_component_count",
        "curriculum_level",
        "marker",
        "alphabetic_section",
        "source_print_page",
        "source_id",
        "part_of_speech",
        "definitions_zh",
        "phonetic_uk",
        "phonetic_us",
        "enrichment_status",
    ]
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            output = dict(record)
            output["official_variants"] = "|".join(record["official_variants"])
            output["part_of_speech"] = ""
            output["definitions_zh"] = ""
            output["phonetic_uk"] = ""
            output["phonetic_us"] = ""
            writer.writerow(output)


def main() -> int:
    source_rows = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(source_rows, list):
        raise SystemExit("Curriculum master must be a JSON array")

    records = build_records(source_rows)
    validation = validate(source_rows, records)
    if not validation["valid"]:
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": "engmaster-clean-curriculum-base",
        "source_id": "moe-hs-english-2017-2020-appendix-2",
        "source_entry_count": len(source_rows),
        "atomic_record_count": len(records),
        "records": records,
    }
    JSON_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(records)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": payload["dataset_id"],
        "generated_by": "tools/build_clean_curriculum_base.py",
        "source_file": str(SOURCE_PATH.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha256_file(SOURCE_PATH),
        **validation,
        "json_sha256": sha256_file(JSON_PATH),
        "csv_sha256": sha256_file(CSV_PATH),
        "content_policy": {
            "legacy_definitions_copied": False,
            "legacy_phonetics_copied": False,
            "legacy_order_used": False,
            "enrichment_fields_initially_empty": True,
        },
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    HASH_PATH.write_text(
        f"{sha256_file(JSON_PATH)}  {JSON_PATH.name}\n"
        f"{sha256_file(CSV_PATH)}  {CSV_PATH.name}\n"
        f"{sha256_file(MANIFEST_PATH)}  {MANIFEST_PATH.name}\n",
        encoding="utf-8",
    )

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
