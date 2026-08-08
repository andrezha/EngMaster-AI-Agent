"""Validate structure and provenance fields in Chinese-definition work batches."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "data_sources/enrichment/chinese_definition_batches"
ALLOWED_DEFINITION_STATUS = {"pending_ai_draft", "ai_draft_complete"}
ALLOWED_QA_STATUS = {"not_checked", "automated_checks_passed", "needs_revision"}
FORBIDDEN_KEYS = {
    "old_definition",
    "old_definitions_zh",
    "ecdict_translation",
    "phonetic_uk",
    "phonetic_us",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument(
        "--mark-passed",
        action="store_true",
        help="mark completed drafts as automated_checks_passed when validation is clean",
    )
    args = parser.parse_args()

    paths = sorted(args.batch_dir.glob("batch_[0-9][0-9][0-9].json"))
    errors: list[str] = []
    warnings: list[str] = []
    all_records: list[dict[str, object]] = []

    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload.get("records", [])
        if payload.get("record_count") != len(records):
            errors.append(f"{path.name}: record_count mismatch")
        all_records.extend(records)

        for record in records:
            rid = str(record.get("record_id", ""))
            forbidden = FORBIDDEN_KEYS & set(record)
            if forbidden:
                errors.append(f"{rid}: forbidden fields: {sorted(forbidden)}")

            status = record.get("definition_status")
            qa_status = record.get("qa_status")
            if status not in ALLOWED_DEFINITION_STATUS:
                errors.append(f"{rid}: invalid definition_status {status!r}")
            if qa_status not in ALLOWED_QA_STATUS:
                errors.append(f"{rid}: invalid qa_status {qa_status!r}")

            definitions = record.get("definitions_zh", [])
            display_pos = record.get("display_parts_of_speech", [])
            selected_ids = record.get("selected_source_sense_ids", [])
            source_ids = {
                sense.get("sense_id") for sense in record.get("candidate_senses", [])
            }
            unknown_ids = set(selected_ids) - source_ids
            if unknown_ids:
                errors.append(f"{rid}: selected unknown sense IDs {sorted(unknown_ids)}")

            if status == "pending_ai_draft":
                if definitions or display_pos or selected_ids:
                    errors.append(f"{rid}: pending record contains completed draft fields")
                continue

            if not definitions:
                errors.append(f"{rid}: completed draft has no Chinese definitions")
            if not display_pos:
                errors.append(f"{rid}: completed draft has no display POS")
            if source_ids and not selected_ids and not record.get("qa_notes"):
                warnings.append(f"{rid}: OEWN senses exist but none selected")
            if not source_ids and not record.get("qa_notes"):
                errors.append(f"{rid}: no OEWN semantics and no supplemental QA note")

            seen_pairs: set[tuple[str, str]] = set()
            for number, definition in enumerate(definitions, start=1):
                if not isinstance(definition, dict):
                    errors.append(f"{rid}: definition {number} is not an object")
                    continue
                pos = str(definition.get("part_of_speech", "")).strip()
                text = str(definition.get("definition", "")).strip()
                if not pos or not text:
                    errors.append(f"{rid}: definition {number} has blank POS/text")
                if pos and pos not in display_pos:
                    errors.append(f"{rid}: definition POS {pos!r} missing from display POS")
                if re.search(r"\s{2,}", text):
                    warnings.append(f"{rid}: repeated whitespace in definition {number}")
                pair = (pos, text)
                if pair in seen_pairs:
                    errors.append(f"{rid}: duplicate definition {number}")
                seen_pairs.add(pair)

    ids = [str(row.get("record_id", "")) for row in all_records]
    duplicate_ids = sorted(key for key, count in Counter(ids).items() if count > 1)
    if duplicate_ids:
        errors.append(f"duplicate record IDs: {duplicate_ids}")
    if len(all_records) != 3800:
        errors.append(f"expected 3800 total records, got {len(all_records)}")

    status_counts = Counter(str(row.get("definition_status")) for row in all_records)
    print(f"batch files: {len(paths)}")
    print(f"records: {len(all_records)}")
    print("definition status: " + json.dumps(status_counts, ensure_ascii=False))
    print(f"warnings: {len(warnings)}")
    for item in warnings[:20]:
        print(f"WARNING: {item}")
    print(f"errors: {len(errors)}")
    for item in errors[:50]:
        print(f"ERROR: {item}")
    if errors:
        raise SystemExit(1)

    if args.mark_passed:
        if warnings:
            raise SystemExit("refusing to mark QA passed while warnings remain")
        for path in paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            changed = False
            for record in payload["records"]:
                if record["definition_status"] == "ai_draft_complete":
                    record["qa_status"] = "automated_checks_passed"
                    changed = True
            if changed:
                path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                    newline="\n",
                )

        def digest(path: Path) -> str:
            return hashlib.sha256(path.read_bytes()).hexdigest()

        manifest_path = args.batch_dir / "batch_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        completed = 0
        passed = 0
        for batch in manifest["batches"]:
            batch_path = args.batch_dir / batch["file"]
            batch["sha256"] = digest(batch_path)
            batch_payload = json.loads(batch_path.read_text(encoding="utf-8"))
            completed += sum(
                row["definition_status"] == "ai_draft_complete"
                for row in batch_payload["records"]
            )
            passed += sum(
                row["qa_status"] == "automated_checks_passed"
                for row in batch_payload["records"]
            )
        manifest["pending_ai_draft_count"] = len(all_records) - completed
        manifest["ai_draft_complete_count"] = completed
        manifest["automated_checks_passed_count"] = passed
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        checksum_targets = sorted(args.batch_dir.glob("batch_*.json")) + [
            args.batch_dir / "README.md"
        ]
        (args.batch_dir / "SHA256SUMS.txt").write_text(
            "\n".join(
                f"{digest(path)}  {path.name}" for path in checksum_targets
            )
            + "\n",
            encoding="ascii",
            newline="\n",
        )
        print(f"marked automated QA passed: {passed}")


if __name__ == "__main__":
    main()
