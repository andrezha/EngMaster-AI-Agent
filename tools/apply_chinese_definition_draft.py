"""Apply a compact, reviewed TSV Chinese-definition draft to one work batch."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH_DIR = ROOT / "data_sources/enrichment/chinese_definition_batches"
DRAFT_DIR = ROOT / "data_sources/enrichment/chinese_definition_drafts"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_definitions(value: str) -> list[dict[str, str]]:
    output = []
    for item in value.split("|"):
        pos, separator, definition = item.partition("=")
        if not separator or not pos.strip() or not definition.strip():
            raise ValueError(f"invalid definition item: {item!r}")
        output.append(
            {"part_of_speech": pos.strip(), "definition": definition.strip()}
        )
    return output


def refresh_evidence_files() -> None:
    manifest_path = BATCH_DIR / "batch_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    completed = 0
    passed = 0
    for batch in manifest["batches"]:
        path = BATCH_DIR / batch["file"]
        batch["sha256"] = sha256(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        completed += sum(
            row["definition_status"] == "ai_draft_complete"
            for row in payload["records"]
        )
        passed += sum(
            row["qa_status"] == "automated_checks_passed"
            for row in payload["records"]
        )
    manifest["pending_ai_draft_count"] = manifest["record_count"] - completed
    manifest["ai_draft_complete_count"] = completed
    manifest["automated_checks_passed_count"] = passed
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    targets = sorted(BATCH_DIR.glob("batch_*.json")) + [BATCH_DIR / "README.md"]
    (BATCH_DIR / "SHA256SUMS.txt").write_text(
        "\n".join(f"{sha256(path)}  {path.name}" for path in targets) + "\n",
        encoding="ascii",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch_number", type=int)
    parser.add_argument("--draft", type=Path)
    args = parser.parse_args()

    batch_name = f"batch_{args.batch_number:03d}"
    batch_path = BATCH_DIR / f"{batch_name}.json"
    draft_path = args.draft or DRAFT_DIR / f"{batch_name}.tsv"
    with draft_path.open("r", encoding="utf-8-sig", newline="") as handle:
        drafts = list(csv.DictReader(handle, delimiter="\t"))
    draft_by_word = {row["word"]: row for row in drafts}
    if len(draft_by_word) != len(drafts):
        raise ValueError("duplicate words in draft TSV")

    payload = json.loads(batch_path.read_text(encoding="utf-8"))
    records = payload["records"]
    words = [record["word"] for record in records]
    if set(words) != set(draft_by_word) or len(words) != len(drafts):
        raise ValueError(
            f"draft/batch mismatch; missing={sorted(set(words)-set(draft_by_word))}; "
            f"extra={sorted(set(draft_by_word)-set(words))}"
        )

    for record in records:
        draft = draft_by_word[record["word"]]
        selected = [x.strip() for x in draft["sense_ids"].split("|") if x.strip()]
        source_ids = {sense["sense_id"] for sense in record["candidate_senses"]}
        unknown = set(selected) - source_ids
        if unknown:
            raise ValueError(f"{record['word']}: unknown sense IDs {sorted(unknown)}")
        definitions = parse_definitions(draft["definitions"])
        notes = [x.strip() for x in draft["notes"].split("|") if x.strip()]
        if source_ids and not selected and not notes:
            raise ValueError(f"{record['word']}: source senses omitted without a note")
        if not source_ids and not notes:
            raise ValueError(f"{record['word']}: supplemental semantics require a note")
        record["selected_source_sense_ids"] = selected
        record["definitions_zh"] = definitions
        record["display_parts_of_speech"] = list(
            dict.fromkeys(item["part_of_speech"] for item in definitions)
        )
        record["definition_status"] = "ai_draft_complete"
        record["qa_status"] = "not_checked"
        record["qa_notes"] = notes

    batch_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    refresh_evidence_files()
    print(f"applied {draft_path.name}: {len(records)} records")


if __name__ == "__main__":
    main()
