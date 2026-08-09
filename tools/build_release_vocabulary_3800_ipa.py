#!/usr/bin/env python3
"""Build a complete, traceable American-IPA layer for the 3800-word release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VOCABULARY_PATH = ROOT / "assets/editions/gaokao/vocabulary.json"
TRIAL_PATH = ROOT / "assets/editions/gaokao/trial_vocabulary.json"
IPA_PATH = ROOT / "data_sources/raw/ipa_dict/en_US.txt"
SOURCE_RECORD_PATH = ROOT / "data_sources/raw/ipa_dict/source.json"
OUTPUT_DIR = ROOT / "data_sources/clean/release_vocabulary_3800_ipa"
OUTPUT_PATH = OUTPUT_DIR / "release_vocabulary_3800_ipa.json"
REPORT_PATH = OUTPUT_DIR / "automated_qa_report.md"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"


SPELLING_ALIASES = {
    "analyse": "analyze",
    "café": "cafe",
    "civilisation": "civilization",
    "criticise": "criticize",
    "flavour": "flavor",
    "gramme": "gram",
    "o’clock": "o'clock",
    "yoghurt": "yogurt",
}

# These 10 entries are deterministic transforms of cited en_US source rows.
# They are kept explicit so every non-direct match can be audited.
DERIVED_PRONUNCIATIONS = {
    "according to": ("/əˈkɔɹdɪŋ tə/", ["according", "to"]),
    "bean curd": ("/ˈbin ˈkɝd/", ["bean", "curd"]),
    "due to": ("/ˈdu tə/", ["due", "to"]),
    "maths": ("/ˈmæθs/", ["math"]),
    "mobile phone": ("/ˈmoʊbəɫ ˈfoʊn/", ["mobile", "phone"]),
    "ought to": ("/ˈɔt tə/", ["ought", "to"]),
    "PE": ("/ˌpiˈi/", ["p", "e"]),
    "schoolbag": ("/ˈskuɫˌbæɡ/", ["school", "bag"]),
    "stomachache": ("/ˈstəməkˌeɪk/", ["stomach", "ache"]),
    "toothache": ("/ˈtuθˌeɪk/", ["tooth", "ache"]),
}

# ipa-dict has only the /roʊ/ line/boat pronunciation for this released
# heteronym, while the product meaning also includes the quarrel sense /raʊ/.
SENSE_VARIANT_ADDITIONS = {
    "row": "/ˈɹoʊ/, /ˈɹaʊ/",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_ipa() -> dict[str, str]:
    result: dict[str, str] = {}
    for line_number, line in enumerate(
            IPA_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            word, pronunciation = line.split("\t", 1)
        except ValueError as exc:
            raise ValueError(f"invalid ipa-dict row {line_number}") from exc
        result.setdefault(word.casefold(), pronunciation.strip())
    return result


def build_rows() -> tuple[list[dict[str, object]], dict[str, int]]:
    vocabulary = json.loads(VOCABULARY_PATH.read_text(encoding="utf-8"))
    ipa = load_ipa()
    rows: list[dict[str, object]] = []
    counts = {
        "direct": 0,
        "spelling_alias": 0,
        "derived": 0,
        "sense_variant_addition": 0,
    }

    for item in vocabulary:
        word = str(item["word"])
        lookup = word.casefold()
        source_entries: list[str]
        if word in SENSE_VARIANT_ADDITIONS:
            if lookup not in ipa:
                raise ValueError(f"missing base IPA row for sense variant {word!r}")
            pronunciation = SENSE_VARIANT_ADDITIONS[word]
            method = "sense_variant_addition"
            source_entries = [word]
        elif lookup in ipa:
            pronunciation = ipa[lookup]
            method = "direct"
            source_entries = [word]
        elif word in SPELLING_ALIASES:
            alias = SPELLING_ALIASES[word]
            pronunciation = ipa[alias.casefold()]
            method = "spelling_alias"
            source_entries = [alias]
        elif word in DERIVED_PRONUNCIATIONS:
            pronunciation, source_entries = DERIVED_PRONUNCIATIONS[word]
            missing_sources = [entry for entry in source_entries if entry.casefold() not in ipa]
            if missing_sources:
                raise ValueError(f"missing derived source rows for {word}: {missing_sources}")
            method = "derived"
        else:
            raise ValueError(f"no traceable pronunciation for {word!r}")

        counts[method] += 1
        rows.append({
            "record_id": item["record_id"],
            "word": word,
            "pronunciation": pronunciation,
            "dialect": "en_US_General_American",
            "source": "open-dict-data/ipa-dict en_US",
            "source_commit": "43c3570eb3553bdd19fccd2bd0091534889af023",
            "match_method": method,
            "source_entries": source_entries,
            "qa_status": "automated_checks_passed",
        })

    if len(rows) != 3800 or len({row["record_id"] for row in rows}) != 3800:
        raise ValueError("IPA layer must contain 3800 unique release record IDs")
    return rows, counts


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def apply_to_product(rows: list[dict[str, object]]) -> None:
    by_id = {str(row["record_id"]): row for row in rows}
    vocabulary = json.loads(VOCABULARY_PATH.read_text(encoding="utf-8"))
    for item in vocabulary:
        ipa_row = by_id[str(item["record_id"])]
        item["pronunciation"] = ipa_row["pronunciation"]
        item["pronunciation_source"] = "ipa-dict en_US"
        item["pronunciation_match_method"] = ipa_row["match_method"]
    write_json(VOCABULARY_PATH, vocabulary)

    trial = json.loads(TRIAL_PATH.read_text(encoding="utf-8"))
    release_by_id = {str(row["record_id"]): row for row in vocabulary}
    write_json(TRIAL_PATH, [release_by_id[str(row["record_id"])] for row in trial])


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, counts = build_rows()
    payload = {
        "schema_version": 1,
        "dataset_id": "engmaster-release-vocabulary-3800-ipa-en-us",
        "generated_on": "2026-08-09",
        "record_count": len(rows),
        "dialect": "General American",
        "records": rows,
    }
    write_json(OUTPUT_PATH, payload)
    apply_to_product(rows)
    REPORT_PATH.write_text(
        "# 3800词美式IPA自动校验报告\n\n"
        f"- 总记录：{len(rows)}\n"
        f"- ipa-dict直接匹配：{counts['direct']}\n"
        f"- 明确拼写映射：{counts['spelling_alias']}\n"
        f"- 由已匹配源词机械组合：{counts['derived']}\n"
        f"- 同形异音义项补全：{counts['sense_variant_addition']}\n"
        "- 空音标：0\n"
        "- 方言：General American（en_US）\n"
        "- 英式en_UK数据：未使用（上游注明其派生自GPL-3.0来源）\n"
        "- 人工逐条审核声明：无\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": 1,
        "source_record": str(SOURCE_RECORD_PATH.relative_to(ROOT)).replace("\\", "/"),
        "source_record_sha256": sha256_file(SOURCE_RECORD_PATH),
        "source_data_sha256": sha256_file(IPA_PATH),
        "output_sha256": sha256_file(OUTPUT_PATH),
        "report_sha256": sha256_file(REPORT_PATH),
        "counts": counts,
        "excluded_sources": ["ipa-dict en_UK"],
    }
    write_json(MANIFEST_PATH, manifest)
    print(json.dumps({"records": len(rows), **counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
