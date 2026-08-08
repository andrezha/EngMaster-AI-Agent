"""Resolve extension form flags and create traceable inclusion-reason candidates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data_sources/processed"
DEFAULT_SCREENING = PROCESSED / "extension_screening_all.csv"
DEFAULT_SCORES = PROCESSED / "extension_relevance_scores_all.csv"
DEFAULT_BASE = ROOT / "data_sources/clean/curriculum_base.json"
DEFAULT_OEWN = ROOT / "data_sources/raw/oewn/english-wordnet-2025-json.zip"
DEFAULT_ECDICT = ROOT / "data_sources/raw/ecdict/ecdict.csv"

FORM_FIELDS = [
    "legacy_word",
    "source_issue",
    "supported_headword",
    "supported_headword_in_curriculum",
    "oewn_exact_lemma",
    "oewn_pos",
    "resolution",
    "reason",
]

REASON_FIELDS = [
    "word",
    "relevance_score",
    "relevance_recommendation",
    "bnc_rank",
    "contemporary_rank",
    "oewn_pos",
    "oewn_lexicographer_classes",
    "theme_candidates",
    "theme_assignment_status",
    "independent_inclusion_reason",
    "final_status",
]

NORMALIZED_FIELDS = [
    "word",
    "replaces_legacy_form",
    "oewn_pos",
    "bnc_rank",
    "contemporary_rank",
    "relevance_score",
    "recommendation",
    "oewn_lexicographer_classes",
    "theme_candidates",
    "independent_inclusion_reason",
    "reason",
]


THEME_MAP = {
    "human_self": {
        "noun.body",
        "noun.cognition",
        "noun.feeling",
        "noun.food",
        "noun.motive",
        "verb.body",
        "verb.cognition",
        "verb.consumption",
        "verb.emotion",
        "verb.perception",
    },
    "human_society": {
        "noun.act",
        "noun.artifact",
        "noun.communication",
        "noun.event",
        "noun.group",
        "noun.person",
        "noun.possession",
        "noun.relation",
        "verb.communication",
        "verb.competition",
        "verb.creation",
        "verb.possession",
        "verb.social",
    },
    "human_nature": {
        "noun.animal",
        "noun.location",
        "noun.object",
        "noun.phenomenon",
        "noun.plant",
        "noun.quantity",
        "noun.shape",
        "noun.substance",
        "noun.time",
        "verb.change",
        "verb.contact",
        "verb.motion",
        "verb.weather",
    },
}

THEME_ZH = {
    "human_self": "人与自我",
    "human_society": "人与社会",
    "human_nature": "人与自然",
    "general_reading": "一般阅读",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_curriculum_words(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    words: set[str] = set()
    for row in data["records"]:
        words.add(row["word"].casefold())
        words.update(form.casefold() for form in row.get("official_variants", []))
    return words


def load_oewn(
    path: Path, wanted: set[str]
) -> tuple[dict[str, dict[str, object]], dict[str, set[str]]]:
    entries: dict[str, dict[str, object]] = {}
    synset_to_class: dict[str, str] = {}
    with zipfile.ZipFile(path) as archive:
        entry_names = sorted(
            name for name in archive.namelist() if Path(name).name.startswith("entries-")
        )
        for name in entry_names:
            data = json.loads(archive.read(name))
            for lemma, by_pos in data.items():
                if lemma.casefold() not in wanted:
                    continue
                synsets: set[str] = set()
                for details in by_pos.values():
                    synsets.update(
                        sense["synset"]
                        for sense in details.get("sense", [])
                        if "synset" in sense
                    )
                entries[lemma.casefold()] = {
                    "lemma": lemma,
                    "pos": sorted(by_pos),
                    "synsets": synsets,
                }
        for name in archive.namelist():
            base = Path(name).name
            if base.startswith("entries-") or not base.endswith(".json"):
                continue
            lexclass = base[:-5]
            if not lexclass.startswith(("noun.", "verb.", "adj.", "adv.")):
                continue
            data = json.loads(archive.read(name))
            for synset_id in data:
                synset_to_class[synset_id] = lexclass

    classes: dict[str, set[str]] = defaultdict(set)
    for folded, entry in entries.items():
        for synset_id in entry["synsets"]:
            lexclass = synset_to_class.get(synset_id)
            if lexclass:
                classes[folded].add(lexclass)
    return entries, classes


def parse_rank(value: str) -> int | None:
    try:
        rank = int(value)
    except (TypeError, ValueError):
        return None
    return rank if rank > 0 else None


def rank_points(rank: int | None) -> int:
    if rank is None:
        return 0
    if rank <= 5_000:
        return 4
    if rank <= 10_000:
        return 3
    if rank <= 20_000:
        return 2
    if rank <= 40_000:
        return 1
    return 0


def load_ecdict(path: Path, wanted: set[str]) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        for row in csv.DictReader(handle):
            folded = row["word"].casefold()
            if folded in wanted and folded not in found:
                found[folded] = {
                    "word": row["word"],
                    "bnc": row["bnc"],
                    "frq": row["frq"],
                }
    return found


def resolve_forms(
    screening: list[dict[str, str]],
    scores: list[dict[str, str]],
    curriculum: set[str],
    oewn_entries: dict[str, dict[str, object]],
) -> tuple[list[dict[str, object]], list[tuple[str, str]]]:
    score_by_word = {row["legacy_word"]: row for row in scores}
    output: list[dict[str, object]] = []
    normalized: list[tuple[str, str]] = []

    for row in screening:
        word = row["legacy_word"]
        recommendation = row["recommendation"]
        scored = score_by_word.get(word)
        flags = scored["form_review_flags"] if scored else ""
        if recommendation != "inflected_form_review" and not flags:
            continue

        entry = oewn_entries.get(word.casefold())
        exact_lemma = bool(entry and entry["lemma"] == word)
        pos = "|".join(entry["pos"]) if entry else row["oewn_pos"]
        supported = row["normalized_headword_candidates"].split(" | ")[0].strip()
        in_curriculum = bool(supported and supported.casefold() in curriculum)

        if recommendation == "inflected_form_review" and in_curriculum:
            resolution = "exclude_redundant_inflection_of_curriculum"
            reason = f"还原词头 {supported} 已在课标母表中；旧屈折形式不另作独立扩展词"
        elif recommendation == "inflected_form_review" and supported:
            resolution = "replace_with_normalized_extension_headword"
            reason = f"将旧表面形式规范为开放词典支持的词头 {supported}，再单独评分"
            normalized.append((supported, word))
        elif flags == "single_letter":
            resolution = "move_to_special_reference_review"
            reason = "单字母条目可能表示字母名、等级或缩写，不作为普通扩展单词处理"
        elif exact_lemma:
            resolution = "keep_confirmed_independent_lemma"
            reason = "虽有词尾形态特征，但 OEWN 将当前拼写作为独立词头收录；保留当前形式并在释义阶段复核"
        else:
            resolution = "manual_form_review"
            reason = "未取得足够的独立词头证据，暂不自动规范化"

        output.append(
            {
                "legacy_word": word,
                "source_issue": recommendation if recommendation == "inflected_form_review" else flags,
                "supported_headword": supported,
                "supported_headword_in_curriculum": "yes" if in_curriculum else "no",
                "oewn_exact_lemma": "yes" if exact_lemma else "no",
                "oewn_pos": pos,
                "resolution": resolution,
                "reason": reason,
            }
        )
    return output, sorted(set(normalized))


def themes_for(classes: set[str]) -> list[str]:
    themes = [theme for theme, members in THEME_MAP.items() if classes & members]
    return themes or ["general_reading"]


def build_reason_rows(
    scores: list[dict[str, str]], classes: dict[str, set[str]]
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for source in scores:
        word = source["legacy_word"]
        lexclasses = sorted(classes.get(word.casefold(), set()))
        themes = themes_for(set(lexclasses))
        bnc = source["bnc_rank"] or "无有效排名"
        contemporary = source["contemporary_rank"] or "无有效排名"
        score = int(source["relevance_score"])
        recommendation = source["recommendation"]
        if recommendation == "frequency_supported_extension":
            status = "priority_candidate_needs_semantic_review"
            reason = f"独立语料频率支持较强（BNC {bnc}；当代语料 {contemporary}；评分 {score}/9）"
        elif recommendation == "secondary_relevance_review":
            status = "pending_theme_review"
            reason = f"独立语料频率支持中等（BNC {bnc}；当代语料 {contemporary}；评分 {score}/9）"
        else:
            status = "hold"
            reason = f"独立语料频率支持不足（BNC {bnc}；当代语料 {contemporary}；评分 {score}/9）"
        rows.append(
            {
                "word": word,
                "relevance_score": score,
                "relevance_recommendation": recommendation,
                "bnc_rank": source["bnc_rank"],
                "contemporary_rank": source["contemporary_rank"],
                "oewn_pos": source["oewn_pos"],
                "oewn_lexicographer_classes": "|".join(lexclasses),
                "theme_candidates": "|".join(THEME_ZH[theme] for theme in themes),
                "theme_assignment_status": "machine_candidate_needs_review",
                "independent_inclusion_reason": reason,
                "final_status": status,
            }
        )
    return rows


def score_normalized(
    pairs: list[tuple[str, str]],
    entries: dict[str, dict[str, object]],
    classes: dict[str, set[str]],
    ecdict: dict[str, dict[str, str]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for word, legacy in pairs:
        evidence = ecdict.get(word.casefold(), {})
        bnc = parse_rank(evidence.get("bnc", ""))
        contemporary = parse_rank(evidence.get("frq", ""))
        score = rank_points(bnc) + rank_points(contemporary) + int(bnc is not None and contemporary is not None)
        if score >= 7:
            rec = "frequency_supported_extension"
        elif score >= 4:
            rec = "secondary_relevance_review"
        else:
            rec = "hold_without_more_evidence"
        entry = entries.get(word.casefold(), {})
        lexclasses = sorted(classes.get(word.casefold(), set()))
        themes = themes_for(set(lexclasses))
        rows.append(
            {
                "word": word,
                "replaces_legacy_form": legacy,
                "oewn_pos": "|".join(entry.get("pos", [])),
                "bnc_rank": bnc if bnc is not None else "",
                "contemporary_rank": contemporary if contemporary is not None else "",
                "relevance_score": score,
                "recommendation": rec,
                "oewn_lexicographer_classes": "|".join(lexclasses),
                "theme_candidates": "|".join(THEME_ZH[theme] for theme in themes),
                "independent_inclusion_reason": f"规范词头的独立语料频率（BNC {bnc if bnc is not None else '无有效排名'}；当代语料 {contemporary if contemporary is not None else '无有效排名'}；评分 {score}/9）",
                "reason": "使用规范词头重新计算独立语料频率；旧词表释义、音标和标签均未沿用",
            }
        )
    return rows


def write_report(
    path: Path,
    form_rows: list[dict[str, object]],
    reason_rows: list[dict[str, object]],
    normalized_rows: list[dict[str, object]],
) -> None:
    resolutions = Counter(str(row["resolution"]) for row in form_rows)
    theme_counts = Counter()
    for row in reason_rows:
        theme_counts.update(str(row["theme_candidates"]).split("|"))
    lines = [
        "# 扩展词词形处理与收录理由报告",
        "",
        "## 词形处理",
        "",
        f"本轮复核 {len(form_rows)} 个带词形标记的项目。机器只依据课标母表和 OEWN 独立词头记录作处理建议，不使用旧中文释义。",
        "",
        "| 处理建议 | 数量 |",
        "| --- | ---: |",
    ]
    for key in sorted(resolutions):
        lines.append(f"| {key} | {resolutions[key]} |")
    lines.extend(["", "规范化后产生的新扩展词头："])
    for row in normalized_rows:
        lines.append(
            f"- `{row['replaces_legacy_form']}` → `{row['word']}`：{row['recommendation']}，评分 {row['relevance_score']}/9"
        )
    lines.extend(
        [
            "",
            "## 主题收录理由",
            "",
            "OEWN 的 lexicographer class 被映射为“人与自我、人与社会、人与自然、一般阅读”的候选标签。一个词可以有多个候选主题。该映射只用于缩小复核范围，不能替代最终义项判断。",
            "",
            "| 主题候选 | 数量（可重复） |",
            "| --- | ---: |",
        ]
    )
    for key in sorted(theme_counts):
        lines.append(f"| {key} | {theme_counts[key]} |")
    lines.extend(
        [
            "",
            "## 使用边界",
            "",
            "- 独立收录理由只引用语料频率、OEWN 词性和语义类别。",
            "- ECDICT 的 `gk` 等考试标签不参与分数或收录理由。",
            "- 当前主题均标记为 `machine_candidate_needs_review`，尚未宣称人工确认。",
            "- 本轮没有修改正式词库。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screening", type=Path, default=DEFAULT_SCREENING)
    parser.add_argument("--scores", type=Path, default=DEFAULT_SCORES)
    parser.add_argument("--curriculum", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--oewn", type=Path, default=DEFAULT_OEWN)
    parser.add_argument("--ecdict", type=Path, default=DEFAULT_ECDICT)
    parser.add_argument("--output-dir", type=Path, default=PROCESSED)
    args = parser.parse_args()

    screening = read_csv(args.screening)
    scores = read_csv(args.scores)
    curriculum = load_curriculum_words(args.curriculum)
    morphology_words = {
        row["legacy_word"].casefold()
        for row in screening
        if row["recommendation"] == "inflected_form_review"
    }
    wanted = {row["legacy_word"].casefold() for row in scores} | morphology_words
    # These are the three possible normalized non-curriculum headwords.
    wanted.update({"bedding", "refreshment", "souvenir"})
    entries, classes = load_oewn(args.oewn, wanted)
    form_rows, normalized_pairs = resolve_forms(screening, scores, curriculum, entries)
    normalized_words = {word.casefold() for word, _ in normalized_pairs}
    ecdict = load_ecdict(args.ecdict, normalized_words)
    normalized_rows = score_normalized(normalized_pairs, entries, classes, ecdict)
    reason_rows = build_reason_rows(scores, classes)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "extension_form_resolution.csv": (FORM_FIELDS, form_rows),
        "extension_normalized_new_headwords.csv": (NORMALIZED_FIELDS, normalized_rows),
        "extension_inclusion_reason_candidates.csv": (REASON_FIELDS, reason_rows),
    }
    written: list[Path] = []
    for filename, (fields, rows) in files.items():
        path = args.output_dir / filename
        write_csv(path, fields, rows)
        written.append(path)
    report = args.output_dir / "extension_form_and_reason_report.md"
    write_report(report, form_rows, reason_rows, normalized_rows)
    written.append(report)
    checksums = args.output_dir / "extension_form_and_reason_SHA256SUMS.txt"
    checksums.write_text(
        "\n".join(f"{sha256(path)}  {path.name}" for path in sorted(written)) + "\n",
        encoding="ascii",
    )

    print(f"Resolved {len(form_rows)} form flags")
    for key, count in sorted(Counter(row["resolution"] for row in form_rows).items()):
        print(f"  {key}: {count}")
    print(f"Generated {len(reason_rows)} inclusion-reason candidates")


if __name__ == "__main__":
    main()
