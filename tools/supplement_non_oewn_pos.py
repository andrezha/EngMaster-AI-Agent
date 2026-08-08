"""Supplement POS evidence for release words that OEWN does not cover."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_DIR = ROOT / "data_sources/enrichment/oewn_semantic_base"
DEFAULT_MISSING = SEMANTIC_DIR / "needs_non_oewn_review.csv"
DEFAULT_SUMMARY = SEMANTIC_DIR / "oewn_semantic_base_summary.csv"
DEFAULT_MOBY = ROOT / "data_sources/raw/moby/mobypos.txt"
DEFAULT_ECDICT = ROOT / "data_sources/raw/ecdict/ecdict.csv"
DEFAULT_OUTPUT = ROOT / "data_sources/enrichment/non_oewn_pos_supplement"

MOBY_POS = {
    "N": "noun",
    "p": "plural_noun",
    "h": "noun_phrase",
    "V": "verb",
    "t": "transitive_verb",
    "i": "intransitive_verb",
    "A": "adjective",
    "v": "adverb",
    "C": "conjunction",
    "P": "preposition",
    "!": "interjection",
    "r": "pronoun",
    "D": "determiner_or_article",
    "I": "indefinite_article",
    "o": "nominative_form",
}

PROPER_NAMES = {
    "Africa", "America", "Australia", "Britain", "Canada", "China", "Confucius",
    "England", "France", "Germany", "India", "Internet", "Japan", "London",
    "Russia", "UK", "US", "Wi-Fi",
}

MANUAL_FALLBACK = {
    "café": ["noun"],
    "due to": ["multiword_preposition"],
    "ice-cream": ["noun", "adjective"],
    "Internet": ["proper_noun", "noun"],
    "o’clock": ["time_expression"],
    "ought to": ["modal_verb_phrase"],
    "Wi-Fi": ["proper_noun", "noun"],
}

FIELDS = [
    "record_id",
    "word",
    "dataset_layer",
    "moby_match_status",
    "moby_matched_forms",
    "moby_raw_codes",
    "moby_parts_of_speech",
    "ecdict_presence_status",
    "ecdict_matched_form",
    "manual_fallback_parts_of_speech",
    "combined_parts_of_speech",
    "item_classification",
    "evidence_status",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_moby(
    path: Path, wanted: set[str]
) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, set[str]]]:
    exact_codes: dict[str, set[str]] = defaultdict(set)
    folded_forms: dict[str, set[str]] = defaultdict(set)
    for line in path.read_text(encoding="latin-1").splitlines():
        if "\\" not in line:
            continue
        form, codes = line.rsplit("\\", 1)
        if form.casefold() not in wanted:
            continue
        exact_codes[form].update(codes)
        folded_forms[form.casefold()].add(form)
    return exact_codes, folded_forms, exact_codes


def choose_moby(
    word: str, exact_codes: dict[str, set[str]], folded_forms: dict[str, set[str]]
) -> tuple[str, list[str]]:
    if word in exact_codes:
        return "exact", [word]
    if word == word.lower():
        forms = sorted(folded_forms.get(word.casefold(), set()), key=str.casefold)
        if forms:
            return "casefold", forms
    return "none", []


def load_ecdict_presence(path: Path, wanted: set[str]) -> dict[str, set[str]]:
    output: dict[str, set[str]] = defaultdict(set)
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        for row in csv.DictReader(handle):
            folded = row["word"].casefold()
            if folded in wanted:
                output[folded].add(row["word"])
    return output


def classify(word: str, parts: set[str]) -> str:
    if word in PROPER_NAMES:
        return "proper_name_or_named_entity"
    if any(char.isspace() for char in word):
        return "curriculum_multiword_expression"
    if parts & {"pronoun", "determiner_or_article", "indefinite_article"}:
        return "function_word_pronoun_or_determiner"
    if parts & {"conjunction", "preposition", "modal_verb_phrase"}:
        return "function_word_connector_or_modal"
    if "interjection" in parts:
        return "interjection"
    return "lexical_or_grammatical_item"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--missing", type=Path, default=DEFAULT_MISSING)
    parser.add_argument("--semantic-summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--moby", type=Path, default=DEFAULT_MOBY)
    parser.add_argument("--ecdict", type=Path, default=DEFAULT_ECDICT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    missing = read_csv(args.missing)
    wanted = {row["word"].casefold() for row in missing}
    exact_codes, folded_forms, code_lookup = load_moby(args.moby, wanted)
    ecdict = load_ecdict_presence(args.ecdict, wanted)

    rows: list[dict[str, object]] = []
    for source in missing:
        word = source["word"]
        match_status, forms = choose_moby(word, exact_codes, folded_forms)
        raw_codes = sorted({code for form in forms for code in code_lookup[form]})
        moby_parts = sorted({MOBY_POS[code] for code in raw_codes if code in MOBY_POS})
        manual_parts = MANUAL_FALLBACK.get(word, [])
        combined = set(moby_parts) | set(manual_parts)
        if word in PROPER_NAMES:
            combined.add("proper_noun")

        ecdict_forms = sorted(ecdict.get(word.casefold(), set()), key=str.casefold)
        if word in ecdict_forms:
            ecdict_status = "exact"
            ecdict_form = word
        elif word == word.lower() and ecdict_forms:
            ecdict_status = "casefold"
            ecdict_form = "|".join(ecdict_forms)
        else:
            ecdict_status = "none"
            ecdict_form = ""
        status = "supplement_pos_ready" if combined else "manual_pos_required"
        rows.append(
            {
                "record_id": source["record_id"],
                "word": word,
                "dataset_layer": source["dataset_layer"],
                "moby_match_status": match_status,
                "moby_matched_forms": "|".join(forms),
                "moby_raw_codes": "|".join(raw_codes),
                "moby_parts_of_speech": "|".join(moby_parts),
                "ecdict_presence_status": ecdict_status,
                "ecdict_matched_form": ecdict_form,
                "manual_fallback_parts_of_speech": "|".join(manual_parts),
                "combined_parts_of_speech": "|".join(sorted(combined)),
                "item_classification": classify(word, combined),
                "evidence_status": status,
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    supplement_path = args.output_dir / "non_oewn_pos_supplement.csv"
    with supplement_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    supplement_by_id = {str(row["record_id"]): row for row in rows}
    semantic = read_csv(args.semantic_summary)
    merged_rows: list[dict[str, object]] = []
    for row in semantic:
        supplement = supplement_by_id.get(row["record_id"])
        if supplement:
            parts = supplement["combined_parts_of_speech"]
            source_name = "Moby POS and/or rule-documented fallback"
            status = supplement["evidence_status"]
        else:
            parts = row["parts_of_speech"]
            source_name = "Open English WordNet 2025"
            status = "pos_evidence_ready"
        merged_rows.append(
            {
                "record_id": row["record_id"],
                "word": row["word"],
                "dataset_layer": row["dataset_layer"],
                "parts_of_speech": parts,
                "pos_evidence_source": source_name,
                "pos_status": status,
            }
        )
    merged_path = args.output_dir / "release_3800_pos_evidence.csv"
    with merged_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "record_id", "word", "dataset_layer", "parts_of_speech",
                "pos_evidence_source", "pos_status",
            ],
        )
        writer.writeheader()
        writer.writerows(merged_rows)

    counts = Counter(str(row["evidence_status"]) for row in rows)
    classes = Counter(str(row["item_classification"]) for row in rows)
    report_path = args.output_dir / "README.md"
    report = [
        "# 非OEWN词性补充报告",
        "",
        f"OEWN未覆盖项目：{len(rows)}。本轮优先使用Moby Part-of-Speech II；ECDICT只检查词形存在性，不提取翻译、释义或音标。少数Moby缺失项使用文件中明确列出的规则化词性补充。",
        "",
        "## 证据状态",
        "",
        "| 状态 | 数量 |",
        "| --- | ---: |",
    ]
    for key in sorted(counts):
        report.append(f"| {key} | {counts[key]} |")
    report.extend(["", "## 项目类型", "", "| 类型 | 数量 |", "| --- | ---: |"])
    for key in sorted(classes):
        report.append(f"| {key} | {classes[key]} |")
    report.extend(
        [
            "",
            "Moby代码是辅助证据，可能包含低频或历史词性；最终面向高中生展示的词性还需在中文释义阶段按实际保留义项收窄。",
            "",
        ]
    )
    report_path.write_text("\n".join(report), encoding="utf-8")
    written = [supplement_path, merged_path, report_path]
    checksums = args.output_dir / "SHA256SUMS.txt"
    checksums.write_text(
        "\n".join(f"{sha256(path)}  {path.name}" for path in sorted(written)) + "\n",
        encoding="ascii",
    )
    print(f"Supplemented {len(rows)} non-OEWN records")
    print(counts)
    print(f"Merged POS evidence rows: {len(merged_rows)}")


if __name__ == "__main__":
    main()
