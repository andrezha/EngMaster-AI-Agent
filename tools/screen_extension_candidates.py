"""First-pass screening for vocabulary candidates outside the curriculum list.

This script deliberately does not copy definitions, translations, or phonetics from
the legacy vocabulary file.  Dictionary presence is evidence that a spelling is a
lexical item, not evidence that it belongs in a high-school learning list.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data_sources/processed/current_vocab_extension_candidates.csv"
DEFAULT_OEWN = ROOT / "data_sources/raw/oewn/english-wordnet-2025-json.zip"
DEFAULT_MOBY_WORDS = ROOT / "data_sources/raw/moby/common.txt"
DEFAULT_MOBY_POS = ROOT / "data_sources/raw/moby/mobypos.txt"
DEFAULT_PHRASES = ROOT / "assets/short_phrase.json"
DEFAULT_OUTPUT = ROOT / "data_sources/processed"


OUTPUT_COLUMNS = [
    "legacy_word",
    "legacy_row_count",
    "legacy_rows",
    "structural_type",
    "oewn_match_type",
    "oewn_lemmas",
    "oewn_pos",
    "oewn_sense_count",
    "moby_wordlist_match_type",
    "moby_wordlist_forms",
    "moby_pos_match_type",
    "moby_pos_forms",
    "moby_pos_codes",
    "normalized_headword_candidates",
    "normalized_headword_evidence",
    "existing_phrase_table_match",
    "lexical_evidence_score",
    "recommendation",
    "reason",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def add_casefold(index: dict[str, set[str]], form: str) -> None:
    index[form.casefold()].add(form)


def load_oewn(path: Path) -> tuple[dict[str, dict[str, object]], dict[str, set[str]]]:
    exact: dict[str, dict[str, object]] = {}
    folded: dict[str, set[str]] = defaultdict(set)
    with zipfile.ZipFile(path) as archive:
        entry_files = sorted(
            name
            for name in archive.namelist()
            if re.search(r"(?:^|/)entries-[^.]+\.json$", name)
        )
        if not entry_files:
            raise RuntimeError(f"No OEWN entries-*.json files found in {path}")
        for name in entry_files:
            data = json.loads(archive.read(name))
            for lemma, by_pos in data.items():
                pos_codes = sorted(by_pos)
                sense_count = sum(
                    len(details.get("sense", [])) for details in by_pos.values()
                )
                exact[lemma] = {"pos": pos_codes, "sense_count": sense_count}
                add_casefold(folded, lemma)
    return exact, folded


def load_line_wordlist(path: Path) -> tuple[set[str], dict[str, set[str]]]:
    exact: set[str] = set()
    folded: dict[str, set[str]] = defaultdict(set)
    for line in path.read_text(encoding="latin-1").splitlines():
        form = line.strip()
        if not form:
            continue
        exact.add(form)
        add_casefold(folded, form)
    return exact, folded


def load_moby_pos(
    path: Path,
) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, set[str]]]:
    exact: dict[str, set[str]] = defaultdict(set)
    folded: dict[str, set[str]] = defaultdict(set)
    for line in path.read_text(encoding="latin-1").splitlines():
        if "\\" not in line:
            continue
        form, codes = line.rsplit("\\", 1)
        form = form.strip()
        if not form:
            continue
        exact[form].update(codes.strip())
        add_casefold(folded, form)
    return exact, folded, exact


def load_phrase_forms(path: Path) -> tuple[set[str], dict[str, set[str]]]:
    exact: set[str] = set()
    folded: dict[str, set[str]] = defaultdict(set)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    for row in data:
        # In this project `p` is the phrase itself; `en` is only an example sentence.
        form = str(row.get("p", "")).strip()
        if not form:
            continue
        exact.add(form)
        add_casefold(folded, form)
    return exact, folded


def lookup(
    word: str, exact: set[str] | dict[str, object], folded: dict[str, set[str]]
) -> tuple[str, list[str]]:
    if word in exact:
        return "exact", [word]
    forms = sorted(folded.get(word.casefold(), set()), key=lambda x: (x.casefold(), x))
    if forms:
        return "casefold", forms
    return "none", []


def structural_type(word: str) -> str:
    letters = "".join(char for char in word if char.isalpha())
    if any(char.isspace() for char in word):
        return "multiword"
    if letters and letters.isupper() and len(letters) > 1:
        return "all_uppercase"
    if word[:1].isupper():
        return "initial_uppercase"
    if "-" in word:
        return "hyphenated"
    return "lowercase_single_word"


def possible_headwords(word: str) -> list[str]:
    """Return conservative spelling candidates for common English inflections."""
    candidates: set[str] = set()
    irregular = {
        "does": {"do"},
    }
    lower = word.casefold()
    if lower in irregular:
        return sorted(irregular[lower])
    if lower.endswith("ies") and len(lower) > 4:
        candidates.add(lower[:-3] + "y")
    if lower.endswith("es") and len(lower) > 3:
        candidates.add(lower[:-2])
        candidates.add(lower[:-1])
    elif lower.endswith("s") and len(lower) > 2 and not lower.endswith("ss"):
        candidates.add(lower[:-1])
    if lower.endswith("ing") and len(lower) > 5:
        stem = lower[:-3]
        if len(stem) > 2 and stem[-1] == stem[-2]:
            candidates.add(stem[:-1])
        else:
            candidates.update({stem, stem + "e"})
    if lower.endswith("ed") and len(lower) > 4:
        stem = lower[:-2]
        if len(stem) > 2 and stem[-1] == stem[-2]:
            candidates.add(stem[:-1])
        else:
            candidates.update({stem, stem + "e"})
    candidates.discard(lower)
    return sorted(candidates)


def find_supported_headwords(
    word: str,
    oewn_exact: dict[str, dict[str, object]],
    oewn_folded: dict[str, set[str]],
    moby_words_exact: set[str],
    moby_words_folded: dict[str, set[str]],
    moby_pos_exact: dict[str, set[str]],
    moby_pos_folded: dict[str, set[str]],
) -> tuple[list[str], list[str]]:
    supported: list[str] = []
    evidence: list[str] = []
    for candidate in possible_headwords(word):
        sources: list[str] = []
        oewn_supported = lookup(candidate, oewn_exact, oewn_folded)[0] != "none"
        if oewn_supported:
            sources.append("OEWN")
        if lookup(candidate, moby_words_exact, moby_words_folded)[0] != "none":
            sources.append("MobyWords")
        if lookup(candidate, moby_pos_exact, moby_pos_folded)[0] != "none":
            sources.append("MobyPOS")
        # OEWN is lemma-oriented. Requiring it here avoids treating arbitrary
        # suffix stripping (for example, "theirs" -> "their") as morphology.
        if oewn_supported:
            supported.append(candidate)
            evidence.append(f"{candidate}:{'+'.join(sources)}")
    return supported, evidence


def matched_oewn_details(
    forms: list[str], oewn_exact: dict[str, dict[str, object]]
) -> tuple[str, int]:
    pos: set[str] = set()
    sense_count = 0
    for form in forms:
        details = oewn_exact.get(form)
        if details:
            pos.update(str(item) for item in details["pos"])
            sense_count += int(details["sense_count"])
    return "|".join(sorted(pos)), sense_count


def screen_row(
    source: dict[str, str],
    oewn_exact: dict[str, dict[str, object]],
    oewn_folded: dict[str, set[str]],
    moby_words_exact: set[str],
    moby_words_folded: dict[str, set[str]],
    moby_pos_exact: dict[str, set[str]],
    moby_pos_folded: dict[str, set[str]],
    phrase_exact: set[str],
    phrase_folded: dict[str, set[str]],
) -> dict[str, object]:
    word = source["legacy_word"].strip()
    structure = structural_type(word)

    oewn_type, oewn_forms = lookup(word, oewn_exact, oewn_folded)
    oewn_pos, sense_count = matched_oewn_details(oewn_forms, oewn_exact)
    mw_type, mw_forms = lookup(word, moby_words_exact, moby_words_folded)
    mp_type, mp_forms = lookup(word, moby_pos_exact, moby_pos_folded)
    pos_codes = sorted(
        {code for form in mp_forms for code in moby_pos_exact.get(form, set())}
    )
    phrase_type, _ = lookup(word, phrase_exact, phrase_folded)
    normalized_forms, normalized_evidence = find_supported_headwords(
        word,
        oewn_exact,
        oewn_folded,
        moby_words_exact,
        moby_words_folded,
        moby_pos_exact,
        moby_pos_folded,
    )

    evidence_score = sum(
        match_type != "none" for match_type in (oewn_type, mw_type, mp_type)
    )

    if structure == "multiword":
        recommendation = "move_to_phrase_review"
        reason = "多词表达不进入单词扩展表；转入短语候选复核"
    elif structure == "all_uppercase":
        recommendation = "special_reference_review"
        reason = "全大写形式可能是缩写、机构名或特殊标签，需单独核实"
    elif structure == "initial_uppercase":
        recommendation = "proper_name_or_capitalization_review"
        if oewn_type == "casefold":
            reason = "开放词典仅以其他大小写形式匹配，需判断是否误大写"
        else:
            reason = "首字母大写形式可能是专名、地域名或误大写，需单独核实"
    elif structure == "hyphenated":
        recommendation = "hyphenated_form_review"
        reason = "连字符形式可能有开放式、闭合式等变体，需确定规范词形"
    elif oewn_type == "none" and normalized_forms:
        recommendation = "inflected_form_review"
        reason = "当前形式可能是复数、第三人称或分词；开放词典支持其候选词头，需决定是否改存词头"
    elif oewn_type != "none" and (mw_type != "none" or mp_type != "none"):
        recommendation = "retain_for_relevance_scoring"
        reason = "OEWN 与至少一个 Moby 数据集均有词形证据；仍需另做学习相关性筛选"
    elif oewn_type != "none":
        recommendation = "modern_lexical_review"
        reason = "OEWN 有词形证据，Moby 未匹配；复核词义、难度与学习价值"
    elif mw_type != "none" or mp_type != "none":
        recommendation = "legacy_lexicon_review"
        reason = "仅 Moby 有词形证据；可能生僻、旧式或专名，需谨慎复核"
    else:
        recommendation = "exclude_or_spelling_review"
        reason = "两个开放词典均无词形证据；优先检查拼写、屈折变化或排除"

    return {
        "legacy_word": word,
        "legacy_row_count": source["legacy_row_count"],
        "legacy_rows": source["legacy_rows"],
        "structural_type": structure,
        "oewn_match_type": oewn_type,
        "oewn_lemmas": " | ".join(oewn_forms),
        "oewn_pos": oewn_pos,
        "oewn_sense_count": sense_count,
        "moby_wordlist_match_type": mw_type,
        "moby_wordlist_forms": " | ".join(mw_forms),
        "moby_pos_match_type": mp_type,
        "moby_pos_forms": " | ".join(mp_forms),
        "moby_pos_codes": "|".join(pos_codes),
        "normalized_headword_candidates": " | ".join(normalized_forms),
        "normalized_headword_evidence": " | ".join(normalized_evidence),
        "existing_phrase_table_match": phrase_type,
        "lexical_evidence_score": evidence_score,
        "recommendation": recommendation,
        "reason": reason,
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sample_words(rows: list[dict[str, object]], limit: int = 12) -> str:
    return "、".join(str(row["legacy_word"]) for row in rows[:limit]) or "（无）"


def write_report(path: Path, rows: list[dict[str, object]]) -> None:
    structures = Counter(str(row["structural_type"]) for row in rows)
    recommendations = Counter(str(row["recommendation"]) for row in rows)
    evidence = Counter(int(row["lexical_evidence_score"]) for row in rows)
    existing_phrase_matches = sum(
        row["existing_phrase_table_match"] != "none" for row in rows
    )

    report = [
        "# 现有扩展词候选第一轮筛查报告",
        "",
        "## 结论边界",
        "",
        "本轮只检查词形结构，以及 OEWN 2025、Moby Words II / Moby Part-of-Speech II 是否收录。词典收录只能证明候选有一定词汇证据，不能证明它适合高中阶段，也不能自动进入发布词库。未复制旧词库的中文释义、音标或例句。",
        "",
        f"- 候选唯一词形：{len(rows)}",
        f"- 已在现有短语表中找到同形短语：{existing_phrase_matches}",
        "",
        "## 按结构分组",
        "",
        "| 结构 | 数量 |",
        "| --- | ---: |",
    ]
    for key in sorted(structures):
        report.append(f"| {key} | {structures[key]} |")
    report.extend(["", "## 初筛建议", "", "| 建议 | 数量 | 示例 |", "| --- | ---: | --- |"])
    for key in sorted(recommendations):
        group = [row for row in rows if row["recommendation"] == key]
        report.append(f"| {key} | {len(group)} | {sample_words(group)} |")
    report.extend(["", "## 开放词汇证据数量", "", "| 命中的数据集数（0–3） | 数量 |", "| ---: | ---: |"])
    for score in range(4):
        report.append(f"| {score} | {evidence[score]} |")
    report.extend(
        [
            "",
            "## 数据来源",
            "",
            "- Open English WordNet 2025 标准版；CC BY 4.0。未使用专名补充包。",
            "- Moby Words II 与 Moby Part-of-Speech II；作者已作公有领域授权声明。",
            "- `assets/short_phrase.json` 仅用 `p` 字段检查已有短语是否同形，不读取或输出中文释义和例句内容。",
            "",
            "## 下一步",
            "",
            "对 `retain_for_relevance_scoring` 和其他人工复核桶建立可解释的学习相关性评分，再决定保留哪些扩展词。短语、专名/缩写、连字符形式分别处理，不直接混入单词母表。",
            "",
        ]
    )
    path.write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--oewn", type=Path, default=DEFAULT_OEWN)
    parser.add_argument("--moby-words", type=Path, default=DEFAULT_MOBY_WORDS)
    parser.add_argument("--moby-pos", type=Path, default=DEFAULT_MOBY_POS)
    parser.add_argument("--phrases", type=Path, default=DEFAULT_PHRASES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    candidates = read_csv(args.input)
    oewn_exact, oewn_folded = load_oewn(args.oewn)
    moby_words_exact, moby_words_folded = load_line_wordlist(args.moby_words)
    moby_pos_exact, moby_pos_folded, moby_pos_codes = load_moby_pos(args.moby_pos)
    phrase_exact, phrase_folded = load_phrase_forms(args.phrases)

    rows = [
        screen_row(
            source,
            oewn_exact,
            oewn_folded,
            moby_words_exact,
            moby_words_folded,
            moby_pos_codes,
            moby_pos_folded,
            phrase_exact,
            phrase_folded,
        )
        for source in candidates
    ]
    rows.sort(key=lambda row: str(row["legacy_word"]).casefold())

    outputs: dict[str, list[dict[str, object]]] = {
        "extension_screening_all.csv": rows,
        "extension_lexical_candidates.csv": [
            row
            for row in rows
            if row["structural_type"] == "lowercase_single_word"
            and row["recommendation"] != "exclude_or_spelling_review"
        ],
        "extension_phrase_candidates.csv": [
            row for row in rows if row["recommendation"] == "move_to_phrase_review"
        ],
        "extension_proper_name_and_abbreviation_candidates.csv": [
            row
            for row in rows
            if row["recommendation"]
            in {"special_reference_review", "proper_name_or_capitalization_review"}
        ],
        "extension_hyphenated_candidates.csv": [
            row for row in rows if row["recommendation"] == "hyphenated_form_review"
        ],
        "extension_weak_or_unverified_candidates.csv": [
            row
            for row in rows
            if row["recommendation"]
            in {"legacy_lexicon_review", "exclude_or_spelling_review"}
        ],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, output_rows in outputs.items():
        path = args.output_dir / filename
        write_csv(path, output_rows)
        written.append(path)

    report_path = args.output_dir / "extension_screening_report.md"
    write_report(report_path, rows)
    written.append(report_path)

    hash_path = args.output_dir / "extension_screening_SHA256SUMS.txt"
    hash_lines = [f"{sha256(path)}  {path.name}" for path in sorted(written)]
    hash_path.write_text("\n".join(hash_lines) + "\n", encoding="ascii")

    print(f"Screened {len(rows)} candidates")
    for recommendation, count in sorted(Counter(row["recommendation"] for row in rows).items()):
        print(f"  {recommendation}: {count}")


if __name__ == "__main__":
    main()
