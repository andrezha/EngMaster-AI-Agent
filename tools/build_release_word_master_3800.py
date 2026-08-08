"""Build the 3,800-record release master and audit overlap with the legacy list."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data_sources/clean"
PROCESSED = ROOT / "data_sources/processed"
DEFAULT_MASTER = CLEAN / "final_word_master/final_word_master.csv"
DEFAULT_OLD = ROOT / "assets/vocabulary.json"
DEFAULT_OUTPUT = CLEAN / "release_word_master_3800"

FIELDS = [
    "record_id",
    "word",
    "variants",
    "dataset_layer",
    "curriculum_level",
    "source_entry",
    "source_sequence",
    "part_of_speech",
    "theme_candidates",
    "selection_route",
    "relevance_score",
    "selection_reason",
    "selection_status",
    "definitions_zh",
    "phonetic_uk",
    "phonetic_us",
]


COMPATIBILITY_VARIANTS = {
    "bean curd": ["beancurd"],
    "cheer": ["cheers"],
    "do": ["does"],
    "grandparent": ["grandparents"],
    "ought to": ["ought"],
    "regard": ["regards"],
    "repair": ["repairs"],
    "score": ["scores"],
    "skip": ["skipping"],
    "souvenir": ["souvenirs"],
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def positive_rank(value: str) -> int | None:
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


def load_rank_evidence(
    priority_path: Path, secondary_path: Path, ecdict_path: Path, wanted: set[str]
) -> dict[str, tuple[int | None, int | None]]:
    evidence: dict[str, tuple[int | None, int | None]] = {}
    for path in [priority_path, secondary_path]:
        for row in read_csv(path):
            evidence[row["word"].casefold()] = (
                positive_rank(row["bnc_rank"]),
                positive_rank(row["contemporary_rank"]),
            )
    missing = wanted - set(evidence)
    if missing:
        with ecdict_path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
            for row in csv.DictReader(handle):
                folded = row["word"].casefold()
                if folded in missing and folded not in evidence:
                    evidence[folded] = (
                        positive_rank(row["bnc"]),
                        positive_rank(row["frq"]),
                    )
    return evidence


def score_and_sort_key(
    row: dict[str, str], evidence: dict[str, tuple[int | None, int | None]]
) -> tuple[object, ...]:
    bnc, contemporary = evidence.get(row["word"].casefold(), (None, None))
    if row["relevance_score"].isdigit():
        score = int(row["relevance_score"])
    else:
        score = rank_points(bnc) + rank_points(contemporary) + int(bnc is not None and contemporary is not None)
    valid = [rank for rank in (bnc, contemporary) if rank is not None]
    coverage = len(valid)
    worst = max(valid) if valid else 999_999
    best = min(valid) if valid else 999_999
    return (-score, -coverage, worst, best, row["word"].casefold())


def forms(rows: list[dict[str, str]]) -> set[str]:
    output: set[str] = set()
    for row in rows:
        output.add(row["word"])
        output.update(item for item in row["variants"].split("|") if item)
    return output


def overlap_stats(rows: list[dict[str, str]], old_words: set[str]) -> dict[str, object]:
    headwords = {row["word"] for row in rows}
    all_forms = forms(rows)
    old_casefold = {word.casefold() for word in old_words}
    form_casefold = {word.casefold() for word in all_forms}
    return {
        "record_count": len(rows),
        "exact_headword_overlap": len(headwords & old_words),
        "old_unique_covered_exact_or_variant": len(old_words & all_forms),
        "old_unique_coverage_rate": len(old_words & all_forms) / len(old_words),
        "old_casefold_coverage_rate": len(old_casefold & form_casefold) / len(old_casefold),
        "new_headword_exact_legacy_rate": len(headwords & old_words) / len(headwords),
        "new_only_headwords": len(headwords - old_words),
        "old_only_forms": len(old_words - all_forms),
    }


def match_legacy_word(word: str, rows: list[dict[str, str]]) -> tuple[str, str]:
    exact_headwords = {row["word"]: row["word"] for row in rows}
    exact_variants: dict[str, set[str]] = {}
    folded_headwords: dict[str, set[str]] = {}
    folded_variants: dict[str, set[str]] = {}
    for row in rows:
        headword = row["word"]
        folded_headwords.setdefault(headword.casefold(), set()).add(headword)
        for variant in filter(None, row["variants"].split("|")):
            exact_variants.setdefault(variant, set()).add(headword)
            folded_variants.setdefault(variant.casefold(), set()).add(headword)
    if word in exact_headwords:
        return "exact_headword", exact_headwords[word]
    if word in exact_variants:
        return "exact_variant", "|".join(sorted(exact_variants[word], key=str.casefold))
    if word.casefold() in folded_headwords:
        return "casefold_headword", "|".join(sorted(folded_headwords[word.casefold()], key=str.casefold))
    if word.casefold() in folded_variants:
        return "casefold_variant", "|".join(sorted(folded_variants[word.casefold()], key=str.casefold))
    return "not_covered", ""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--legacy", type=Path, default=DEFAULT_OLD)
    parser.add_argument("--target", type=int, default=3800)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    full = read_csv(args.master)
    old_data = json.loads(args.legacy.read_text(encoding="utf-8-sig"))
    old_list = [str(row.get("word", "")).strip() for row in old_data if str(row.get("word", "")).strip()]
    old_words = set(old_list)
    # Measure the existing 4,012-record table before adding release-only
    # compatibility aliases below.
    full_stats = overlap_stats(full, old_words)
    curriculum = [row for row in full if row["dataset_layer"] == "curriculum"]
    extensions = [row for row in full if row["dataset_layer"] == "extension"]
    extension_capacity = args.target - len(curriculum)
    if extension_capacity <= 0:
        raise RuntimeError("Target is not larger than the curriculum base")

    evidence = load_rank_evidence(
        CLEAN / "extension_priority_draft/extension_priority_draft.csv",
        CLEAN / "extension_secondary_review/extension_secondary_review_queue.csv",
        ROOT / "data_sources/raw/ecdict/ecdict.csv",
        {row["word"].casefold() for row in extensions},
    )
    ranked = sorted(extensions, key=lambda row: score_and_sort_key(row, evidence))
    selected = ranked[:extension_capacity]
    removed = ranked[extension_capacity:]

    # Preserve confirmed orthographic/morphological forms as aliases without
    # increasing the learning-record count.
    for row in curriculum + selected:
        additions = COMPATIBILITY_VARIANTS.get(row["word"], [])
        variants = [item for item in row["variants"].split("|") if item]
        for item in additions:
            if item not in variants:
                variants.append(item)
        row["variants"] = "|".join(variants)

    release = curriculum + sorted(selected, key=lambda row: row["word"].casefold())
    for index, row in enumerate(release, start=1):
        row["record_id"] = f"release-word-{index:04d}"
        row["selection_status"] = "release_english_scope_frozen"

    release_stats = overlap_stats(release, old_words)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "release_word_master_3800.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(release)
    json_path = args.output_dir / "release_word_master_3800.json"
    json_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dataset_id": "engmaster-release-word-master-3800",
                "status": "release_english_scope_frozen",
                "record_count": len(release),
                "curriculum_record_count": len(curriculum),
                "extension_record_count": len(selected),
                "records": release,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    removed_path = args.output_dir / "extensions_removed_for_3800_target.csv"
    removed_fields = ["word", "selection_route", "relevance_score", "part_of_speech", "theme_candidates", "selection_reason"]
    with removed_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=removed_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(removed)

    legacy_counts = Counter(old_list)
    overlap_mapping: list[dict[str, object]] = []
    for word in sorted(old_words, key=lambda item: (item.casefold(), item)):
        full_status, full_matches = match_legacy_word(word, full)
        release_status, release_matches = match_legacy_word(word, release)
        overlap_mapping.append(
            {
                "legacy_word": word,
                "legacy_row_count": legacy_counts[word],
                "full_4012_status": full_status,
                "full_4012_matched_headwords": full_matches,
                "release_3800_status": release_status,
                "release_3800_matched_headwords": release_matches,
            }
        )
    mapping_path = args.output_dir / "legacy_word_overlap_mapping.csv"
    with mapping_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "legacy_word",
                "legacy_row_count",
                "full_4012_status",
                "full_4012_matched_headwords",
                "release_3800_status",
                "release_3800_matched_headwords",
            ],
        )
        writer.writeheader()
        writer.writerows(overlap_mapping)

    report_path = args.output_dir / "legacy_overlap_and_size_report.md"
    cutoff_key = score_and_sort_key(selected[-1], evidence)
    report_path.write_text(
        "# 新旧词表重合度与3800词发行版报告\n\n"
        "## 老词表基数\n\n"
        f"- 老表数据行：{len(old_list)}\n"
        f"- 老表唯一精确词形：{len(old_words)}\n\n"
        "## 4012词完整候选母表\n\n"
        f"- 老表唯一词形被新表词头或变体覆盖：{full_stats['old_unique_covered_exact_or_variant']}/{len(old_words)}（{full_stats['old_unique_coverage_rate']:.2%}）\n"
        f"- 新表词头可在老表精确找到：{full_stats['exact_headword_overlap']}/{full_stats['record_count']}（{full_stats['new_headword_exact_legacy_rate']:.2%}）\n\n"
        "## 3800词发行版\n\n"
        f"- 课标记录：{len(curriculum)}\n"
        f"- 拓展记录：{len(selected)}\n"
        f"- 合计：{len(release)}\n"
        f"- 老表唯一词形被发行版词头或变体覆盖：{release_stats['old_unique_covered_exact_or_variant']}/{len(old_words)}（{release_stats['old_unique_coverage_rate']:.2%}）\n"
        f"- 忽略大小写后的老表覆盖率：{release_stats['old_casefold_coverage_rate']:.2%}\n"
        f"- 发行版词头可在老表精确找到：{release_stats['exact_headword_overlap']}/{len(release)}（{release_stats['new_headword_exact_legacy_rate']:.2%}）\n"
        f"- 新增词头：{release_stats['new_only_headwords']}，主要是补齐的课标词\n\n"
        "## 缩减规则\n\n"
        "课标3004条全部保留。拓展词使用已经确定的BNC/当代语料综合分数排序；同分时依次优先保留两套语料都有排名、较弱一套排名更高、较强一套排名更高的词。旧表是否收录不参与排序，只用于结果重合度审计。\n\n"
        f"本轮从1008个拓展词中保留{len(selected)}个、移出{len(removed)}个。截断边界排序键为 `{cutoff_key}`。被移出的词继续保存在审计文件中，可恢复，不作删除。\n\n"
        "3800是产品容量目标，不是教育部门公布的固定考试词数。\n",
        encoding="utf-8",
    )

    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "dataset_id": "engmaster-release-word-master-3800",
                "status": "release_english_scope_frozen",
                "record_count": len(release),
                "curriculum_record_count": len(curriculum),
                "extension_record_count": len(selected),
                "removed_extension_count": len(removed),
                "legacy_rows": len(old_list),
                "legacy_unique_exact_words": len(old_words),
                "overlap": release_stats,
                "definitions_and_phonetics_status": "intentionally_blank",
                "legacy_content_reused": False,
                "target_note": "Product-size target only; not an official examination word count.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    readme_path = args.output_dir / "README.md"
    readme_path.write_text(
        "# 3800词发行母表\n\n"
        f"最终发行范围为 {len(release)} 条：课标 {len(curriculum)} 条，拓展 {len(selected)} 条。\n\n"
        f"按词头和已确认变体计算，覆盖老表 {release_stats['old_unique_coverage_rate']:.2%} 的唯一词形；"
        f"发行版中 {release_stats['new_headword_exact_legacy_rate']:.2%} 的词头可在老表精确找到。\n\n"
        "释义和音标字段仍为空；本目录尚未写回应用正式数据。\n",
        encoding="utf-8",
    )

    written = [csv_path, json_path, removed_path, mapping_path, report_path, manifest_path, readme_path]
    checksum_path = args.output_dir / "SHA256SUMS.txt"
    checksum_path.write_text(
        "\n".join(f"{sha256(path)}  {path.name}" for path in sorted(written)) + "\n",
        encoding="ascii",
    )

    print(f"Built {len(release)} records: {len(curriculum)} curriculum + {len(selected)} extension")
    print(f"Legacy unique coverage: {release_stats['old_unique_coverage_rate']:.2%}")
    print(f"Release headwords exact in legacy: {release_stats['new_headword_exact_legacy_rate']:.2%}")
    print(f"Removed extension audit rows: {len(removed)}")


if __name__ == "__main__":
    main()
