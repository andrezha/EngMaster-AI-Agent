"""Validate clean product candidates against application schema behavior."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from phrase_irregular_module import (  # noqa: E402
    _accepted_phrase_answers,
    _phrase_level_groups,
    _visible_phrase_items,
)


DATA_DIR = ROOT / "data_sources/clean/phrase_product_candidates"
MANIFEST = DATA_DIR / "manifest.json"
REPORT = DATA_DIR / "validation_report.json"
EXPECTED = {"junior": 250, "senior_high": 450, "cet4": 750, "cet6": 1050}
REQUIRED_FIELDS = {
    "id", "p", "m", "en", "cn", "answers", "tier", "level",
    "edition", "introduced_level", "usage_note", "source_record_id",
    "form_evidence", "content_method", "data_status", "human_review_claimed",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for name, expected_hash in manifest["file_sha256"].items():
        path = DATA_DIR / name
        if not path.exists() or sha256_file(path) != expected_hash:
            errors.append(f"missing file or hash mismatch: {name}")

    counts: dict[str, int] = {}
    group_counts: dict[str, int] = {}
    for edition_id, expected_count in EXPECTED.items():
        path = DATA_DIR / f"{edition_id}_phrases_product_candidate.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        counts[edition_id] = len(rows)
        if len(rows) != expected_count:
            errors.append(f"{edition_id}: expected {expected_count}, found {len(rows)}")
        if len({row.get("id") for row in rows}) != len(rows):
            errors.append(f"{edition_id}: duplicate id")
        if len({row.get("p") for row in rows}) != len(rows):
            errors.append(f"{edition_id}: duplicate phrase")
        for sequence, row in enumerate(rows, start=1):
            label = f"{edition_id}:{sequence}"
            if set(row) != REQUIRED_FIELDS:
                errors.append(f"{label}: invalid fields")
            for field in ("id", "p", "m", "en", "cn", "usage_note"):
                if not str(row.get(field, "")).strip():
                    errors.append(f"{label}: empty {field}")
            if row.get("answers", [None])[0] != row.get("p"):
                errors.append(f"{label}: primary answer is not phrase")
            if row.get("p", "") not in _accepted_phrase_answers(row):
                errors.append(f"{label}: application answer checker rejects primary phrase")
            if row.get("tier") != "core":
                errors.append(f"{label}: tier must be core")
            if row.get("level") != (sequence - 1) // 50 + 1:
                errors.append(f"{label}: invalid level")
            if row.get("edition") != edition_id:
                errors.append(f"{label}: edition mismatch")
            if row.get("human_review_claimed") is not False:
                errors.append(f"{label}: human_review_claimed must be false")
            if "/" in row.get("p", ""):
                errors.append(f"{label}: slash in phrase")
        visible = _visible_phrase_items(rows)
        if visible != rows:
            errors.append(f"{edition_id}: application visibility filter removed rows")
        groups = _phrase_level_groups(rows)
        group_counts[edition_id] = len(groups)
        if any(len(group["items"]) != 50 for group in groups):
            errors.append(f"{edition_id}: non-50-item application level")

    if manifest.get("legacy_content_reused") is not False:
        errors.append("manifest must record legacy_content_reused=false")
    if manifest.get("formal_product_paths_changed") is not False:
        errors.append("formal product paths must remain unchanged at candidate stage")

    report = {
        "status": "pass" if not errors else "fail",
        "candidate_counts": counts,
        "application_level_counts": group_counts,
        "errors": errors,
        "warnings": warnings,
        "legacy_content_reused": False,
        "formal_product_paths_changed": False,
        "human_review_claimed": False,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
