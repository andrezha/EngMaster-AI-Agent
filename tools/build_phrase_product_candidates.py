"""Adapt clean cumulative phrase releases to the application's phrase schema."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data_sources/clean/phrase_master_content"
OUTPUT_DIR = ROOT / "data_sources/clean/phrase_product_candidates"
SOURCES = {
    "junior": "junior_phrases_250.json",
    "senior_high": "senior_high_phrases_450.json",
    "cet4": "cet4_phrases_750.json",
    "cet6": "cet6_phrases_1050.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def adapt(edition_id: str, rows: list[dict[str, object]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for sequence, row in enumerate(rows, start=1):
        phrase = str(row["phrase"])
        variants = [str(value) for value in row.get("accepted_variants", [])]
        answers = list(dict.fromkeys([phrase, *variants]))
        output.append(
            {
                "id": row["record_id"],
                "p": phrase,
                "m": row["meaning_zh"],
                "en": row["example_en"],
                "cn": row["example_zh"],
                "answers": answers,
                "tier": "core",
                "level": (sequence - 1) // 50 + 1,
                "edition": edition_id,
                "introduced_level": row["introduced_level"],
                "usage_note": row["usage_note_zh"],
                "source_record_id": row["record_id"],
                "form_evidence": row["form_evidence"],
                "content_method": row["content_method"],
                "data_status": "product_candidate_auto_validated",
                "human_review_claimed": False,
            }
        )
    return output


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_paths: list[Path] = []
    counts: dict[str, int] = {}
    level_counts: dict[str, int] = {}
    for edition_id, source_name in SOURCES.items():
        source_path = SOURCE_DIR / source_name
        source_rows = json.loads(source_path.read_text(encoding="utf-8"))
        product_rows = adapt(edition_id, source_rows)
        output_path = OUTPUT_DIR / f"{edition_id}_phrases_product_candidate.json"
        output_path.write_text(
            json.dumps(product_rows, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        output_paths.append(output_path)
        counts[edition_id] = len(product_rows)
        level_counts[edition_id] = max(row["level"] for row in product_rows)

    hashes = {path.name: sha256_file(path) for path in output_paths}
    manifest = {
        "status": "product_candidates_complete",
        "source_directory": str(SOURCE_DIR.relative_to(ROOT)).replace("\\", "/"),
        "candidate_counts": counts,
        "fifty_item_level_counts": level_counts,
        "application_fields": ["id", "p", "m", "en", "cn", "answers", "tier", "level"],
        "legacy_schema_reference": "assets/short_phrase.json",
        "legacy_file_read_for_schema_only": True,
        "legacy_content_reused": False,
        "formal_product_paths_changed": False,
        "human_review_claimed": False,
        "file_sha256": hashes,
    }
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checksum_lines = [f"{digest}  {name}" for name, digest in sorted(hashes.items())]
    checksum_lines.append(f"{sha256_file(manifest_path)}  {manifest_path.name}")
    (OUTPUT_DIR / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
