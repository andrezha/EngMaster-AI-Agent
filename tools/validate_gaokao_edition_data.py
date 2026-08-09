"""Validate the isolated gaokao product data package and its manifest."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "assets/editions/gaokao"
EXPECTED_COUNTS = {
    "vocabulary.json": 3800,
    "trial_vocabulary.json": 30,
    "phrases.json": 450,
    "irregular_verbs.json": 126,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_list(name: str) -> list[dict[str, object]]:
    payload = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise ValueError(f"{name} must contain a JSON object list")
    return payload


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    rows_by_file: dict[str, list[dict[str, object]]] = {}
    for name, expected in EXPECTED_COUNTS.items():
        try:
            rows = load_list(name)
            rows_by_file[name] = rows
            if len(rows) != expected:
                errors.append(f"{name}: expected {expected}, found {len(rows)}")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{name}: {exc}")

    vocabulary = rows_by_file.get("vocabulary.json", [])
    trial_vocabulary = rows_by_file.get("trial_vocabulary.json", [])
    words = [str(row.get("word", "")).strip() for row in vocabulary]
    if len(set(words)) != len(words):
        errors.append("vocabulary.json: duplicate exact headwords")
    case_groups: dict[str, set[str]] = {}
    for word in words:
        case_groups.setdefault(word.casefold(), set()).add(word)
    case_distinct = [
        sorted(values) for values in case_groups.values() if len(values) > 1
    ]
    if case_distinct:
        warnings.append(
            "intentional case-distinct headwords: "
            + ", ".join("/".join(values) for values in case_distinct)
        )
    for index, row in enumerate(vocabulary, start=1):
        if not row.get("word") or not re.search(r"[\u3400-\u9fff]", str(row.get("content", ""))):
            errors.append(f"vocabulary.json row {index}: missing word or Chinese content")
        if row.get("qa_status") != "automated_checks_passed":
            errors.append(f"vocabulary.json row {index}: QA status is not passed")
        variants = [
            value.strip()
            for value in str(row.get("variants", "")).split(";")
            if value.strip()
        ]
        if variants and row.get("accepted_answers") != variants:
            errors.append(f"vocabulary.json row {index}: accepted variants differ")

    release_by_record_id = {
        str(row.get("record_id", "")): row for row in vocabulary
    }
    trial_ids = [str(row.get("record_id", "")) for row in trial_vocabulary]
    if len(set(trial_ids)) != len(trial_ids):
        errors.append("trial_vocabulary.json: duplicate record IDs")
    for index, row in enumerate(trial_vocabulary, start=1):
        if release_by_record_id.get(str(row.get("record_id", ""))) != row:
            errors.append(
                f"trial_vocabulary.json row {index}: not an exact release row"
            )

    phrases = rows_by_file.get("phrases.json", [])
    phrase_ids: set[str] = set()
    for index, row in enumerate(phrases, start=1):
        required = ("id", "p", "m", "en", "cn", "answers", "tier", "level")
        if any(not row.get(field) for field in required):
            errors.append(f"phrases.json row {index}: incomplete application fields")
        phrase_ids.add(str(row.get("id", "")))
        expected_tier = "core" if index <= 300 else "extension"
        expected_level = (
            (index - 1) // 50 + 1
            if expected_tier == "core"
            else (index - 301) // 50 + 1
        )
        if row.get("tier") != expected_tier:
            errors.append(f"phrases.json row {index}: invalid tier")
        if row.get("level") != expected_level:
            errors.append(f"phrases.json row {index}: invalid 50-item level")
        if row.get("human_review_claimed") is not False:
            errors.append(f"phrases.json row {index}: invalid review claim")
    if len(phrase_ids) != len(phrases):
        errors.append("phrases.json: duplicate IDs")

    irregulars = rows_by_file.get("irregular_verbs.json", [])
    infinitives: set[str] = set()
    for index, row in enumerate(irregulars, start=1):
        required = ("infinitive", "past_tense", "past_participle", "meaning")
        if any(not row.get(field) for field in required):
            errors.append(f"irregular_verbs.json row {index}: incomplete application fields")
        infinitives.add(str(row.get("infinitive", "")).casefold())
        if row.get("qa_status") != "automated_checks_passed":
            errors.append(f"irregular_verbs.json row {index}: QA status is not passed")
    if len(infinitives) != len(irregulars):
        errors.append("irregular_verbs.json: duplicate infinitives")

    try:
        manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))
        for name, digest in manifest.get("product_files", {}).items():
            path = DATA_DIR / name
            if not path.exists() or sha256_file(path) != digest:
                errors.append(f"manifest hash mismatch: {name}")
        policy = manifest.get("content_policy", {})
        for key in ("images_included", "audio_included", "phonetics_included", "human_review_claimed"):
            if policy.get(key) is not False:
                errors.append(f"manifest content policy must set {key}=false")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"manifest.json: {exc}")

    for name in (
        "README.md",
        "THIRD_PARTY_NOTICES.md",
        "OPEN_ENGLISH_WORDNET_LICENSE.md",
    ):
        if not (DATA_DIR / name).is_file():
            errors.append(f"missing required notice: {name}")

    report = {
        "status": "pass" if not errors else "fail",
        "counts": {name: len(rows_by_file.get(name, [])) for name in EXPECTED_COUNTS},
        "phrase_tier_counts": {
            "core": sum(row.get("tier") == "core" for row in phrases),
            "extension": sum(row.get("tier") == "extension" for row in phrases),
        },
        "phrase_level_counts": {
            tier: len({row.get("level") for row in phrases if row.get("tier") == tier})
            for tier in ("core", "extension")
        },
        "errors": errors,
        "warnings": warnings,
    }
    (DATA_DIR / "validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
