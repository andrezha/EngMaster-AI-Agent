"""Score screened extension words using independent corpus-frequency evidence.

The ECDICT `gk` tag is retained for provenance auditing but deliberately excluded
from scoring: its near-total overlap with the legacy list makes it circular evidence.
No definitions, translations, phonetics, examples, or audio fields are read into
the generated evidence files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES = ROOT / "data_sources/processed/extension_screening_all.csv"
DEFAULT_ECDICT = ROOT / "data_sources/raw/ecdict/ecdict.csv"
DEFAULT_OUTPUT = ROOT / "data_sources/processed"

FIELDS = [
    "legacy_word",
    "legacy_row_count",
    "legacy_rows",
    "oewn_pos",
    "oewn_sense_count",
    "lexical_evidence_score",
    "ecdict_word",
    "ecdict_match_type",
    "ecdict_tags_audit_only",
    "ecdict_gk_tag",
    "bnc_rank",
    "contemporary_rank",
    "bnc_points",
    "contemporary_points",
    "cross_corpus_bonus",
    "relevance_score",
    "frequency_profile",
    "form_review_flags",
    "recommendation",
    "reason",
]


def load_candidates(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if row["recommendation"] == "retain_for_relevance_scoring"]


def load_ecdict_evidence(
    path: Path, wanted: dict[str, str]
) -> dict[str, dict[str, str]]:
    evidence: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        required = {"word", "tag", "bnc", "frq"}
        if not required.issubset(reader.fieldnames or []):
            raise RuntimeError(f"ECDICT fields missing: {required - set(reader.fieldnames or [])}")
        for row in reader:
            folded = row["word"].casefold()
            if folded not in wanted:
                continue
            current = evidence.get(folded)
            # Prefer an exact-case entry if the source ever contains case variants.
            if current is None or (
                row["word"] == wanted[folded] and current["word"] != wanted[folded]
            ):
                evidence[folded] = {
                    "word": row["word"],
                    "tag": row["tag"],
                    "bnc": row["bnc"],
                    "frq": row["frq"],
                }
    return evidence


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


def frequency_profile(bnc: int | None, contemporary: int | None) -> str:
    if bnc is None and contemporary is None:
        return "no_frequency_rank"
    if bnc is None or contemporary is None:
        return "single_corpus_only"
    worse = max(bnc, contemporary)
    better = min(bnc, contemporary)
    if worse <= 10_000:
        return "strong_in_both_corpora"
    if better <= 10_000 and worse <= 20_000:
        return "strong_with_moderate_cross_corpus_support"
    if better <= 10_000:
        return "mixed_between_corpora"
    if better <= 20_000:
        return "moderate_frequency"
    return "limited_frequency"


def form_flags(word: str) -> str:
    flags: list[str] = []
    if len(word) == 1:
        flags.append("single_letter")
    if word.endswith("s") and not word.endswith(("ss", "us", "is")):
        flags.append("possible_plural_or_third_person")
    if word.endswith("ing"):
        flags.append("possible_participle_or_gerund")
    if word.endswith("ed"):
        flags.append("possible_participle_or_adjective")
    return "|".join(flags)


def score_row(source: dict[str, str], evidence: dict[str, str]) -> dict[str, object]:
    word = source["legacy_word"]
    bnc = positive_rank(evidence.get("bnc", ""))
    contemporary = positive_rank(evidence.get("frq", ""))
    bnc_score = rank_points(bnc)
    contemporary_score = rank_points(contemporary)
    coverage_bonus = int(bnc is not None and contemporary is not None)
    score = bnc_score + contemporary_score + coverage_bonus
    flags = form_flags(word)

    if score >= 7:
        recommendation = "frequency_supported_extension"
        reason = "两套语料频率综合证据较强；可作为拓展词优先候选，但仍需词形和义项检查"
    elif score >= 4:
        recommendation = "secondary_relevance_review"
        reason = "频率证据中等或两套语料差异较大；需结合高中阅读主题复核"
    else:
        recommendation = "hold_without_more_evidence"
        reason = "独立频率证据较弱或不完整；没有其他证据前暂不纳入"
    if flags:
        reason += "；另有词形复核标记"

    tags = evidence.get("tag", "").split()
    match_type = "exact" if evidence.get("word") == word else "casefold"
    return {
        "legacy_word": word,
        "legacy_row_count": source["legacy_row_count"],
        "legacy_rows": source["legacy_rows"],
        "oewn_pos": source["oewn_pos"],
        "oewn_sense_count": source["oewn_sense_count"],
        "lexical_evidence_score": source["lexical_evidence_score"],
        "ecdict_word": evidence.get("word", ""),
        "ecdict_match_type": match_type if evidence else "none",
        "ecdict_tags_audit_only": " ".join(tags),
        "ecdict_gk_tag": "yes" if "gk" in tags else "no",
        "bnc_rank": bnc if bnc is not None else "",
        "contemporary_rank": contemporary if contemporary is not None else "",
        "bnc_points": bnc_score,
        "contemporary_points": contemporary_score,
        "cross_corpus_bonus": coverage_bonus,
        "relevance_score": score,
        "frequency_profile": frequency_profile(bnc, contemporary),
        "form_review_flags": flags,
        "recommendation": recommendation,
        "reason": reason,
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def sample(rows: list[dict[str, object]], limit: int = 15) -> str:
    return "、".join(str(row["legacy_word"]) for row in rows[:limit]) or "（无）"


def write_report(path: Path, rows: list[dict[str, object]]) -> None:
    recs = Counter(str(row["recommendation"]) for row in rows)
    profiles = Counter(str(row["frequency_profile"]) for row in rows)
    scores = Counter(int(row["relevance_score"]) for row in rows)
    gk_count = sum(row["ecdict_gk_tag"] == "yes" for row in rows)
    form_count = sum(bool(row["form_review_flags"]) for row in rows)
    missing_count = sum(row["ecdict_match_type"] == "none" for row in rows)

    lines = [
        "# 扩展词高中学习相关性评分报告",
        "",
        "## 核心结论",
        "",
        f"本轮对第一轮筛查通过的 {len(rows)} 个普通扩展词进行独立频率评分。ECDICT 只提取精确词形、BNC 排名、当代语料排名和审计标签；不提取、不输出中文释义、英文释义、音标、例句及音频字段。",
        "",
        f"- ECDICT 精确或大小写匹配：{len(rows) - missing_count}/{len(rows)}",
        f"- 带 ECDICT `gk` 标签：{gk_count}/{len(rows)}（{gk_count / len(rows):.1%}）",
        f"- 带自动词形复核标记：{form_count}",
        "",
        "`gk` 标签与旧候选表重合过高，表明二者可能同源或曾相互引用。为避免循环论证，`gk`、`zk`、`cet4`、Oxford、Collins 等标签均不计入本轮分数。",
        "",
        "## 评分规则",
        "",
        "BNC 和当代语料分别计分：排名 1–5000 得4分，5001–10000得3分，10001–20000得2分，20001–40000得1分，缺失或超过40000得0分；两套语料都有有效排名再加1分。总分0–9。",
        "",
        "- 7–9分：频率支持较强，作为拓展词优先候选。",
        "- 4–6分：进入高中阅读主题和词形二次复核。",
        "- 0–3分：没有更多独立证据前暂不纳入。",
        "",
        "频率高不等于一定适合高中教学；频率低也不等于词本身错误。本结果是可复算的机器分层，不是最终发布清单。",
        "",
        "## 分档结果",
        "",
        "| 建议 | 数量 | 示例 |",
        "| --- | ---: | --- |",
    ]
    for key in [
        "frequency_supported_extension",
        "secondary_relevance_review",
        "hold_without_more_evidence",
    ]:
        group = [row for row in rows if row["recommendation"] == key]
        lines.append(f"| {key} | {len(group)} | {sample(group)} |")
    lines.extend(["", "## 频率画像", "", "| 画像 | 数量 |", "| --- | ---: |"])
    for key in sorted(profiles):
        lines.append(f"| {key} | {profiles[key]} |")
    lines.extend(["", "## 分数分布", "", "| 分数 | 数量 |", "| ---: | ---: |"])
    for score in range(10):
        lines.append(f"| {score} | {scores[score]} |")
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "先对中档和词形标记项进行规则化处理，再按高中阅读主题（人与自我、人与社会、人与自然及常见学科阅读）补充收录理由。只有具备明确理由的词才进入最终 `extension` 层。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--ecdict", type=Path, default=DEFAULT_ECDICT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    candidates = load_candidates(args.candidates)
    wanted = {row["legacy_word"].casefold(): row["legacy_word"] for row in candidates}
    if len(wanted) != len(candidates):
        raise RuntimeError("Candidate casefold collision detected")
    evidence = load_ecdict_evidence(args.ecdict, wanted)
    missing = sorted(set(wanted) - set(evidence))
    if missing:
        raise RuntimeError(f"ECDICT evidence missing for {len(missing)} candidates: {missing[:10]}")

    rows = [score_row(row, evidence[row["legacy_word"].casefold()]) for row in candidates]
    rows.sort(key=lambda row: str(row["legacy_word"]).casefold())
    output_groups = {
        "extension_relevance_scores_all.csv": rows,
        "extension_frequency_supported.csv": [
            row for row in rows if row["recommendation"] == "frequency_supported_extension"
        ],
        "extension_secondary_relevance_review.csv": [
            row for row in rows if row["recommendation"] == "secondary_relevance_review"
        ],
        "extension_hold_without_more_evidence.csv": [
            row for row in rows if row["recommendation"] == "hold_without_more_evidence"
        ],
        "extension_form_review_flags.csv": [row for row in rows if row["form_review_flags"]],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, group in output_groups.items():
        path = args.output_dir / filename
        write_csv(path, group)
        written.append(path)
    report = args.output_dir / "extension_relevance_scoring_report.md"
    write_report(report, rows)
    written.append(report)
    checksums = args.output_dir / "extension_relevance_SHA256SUMS.txt"
    checksums.write_text(
        "\n".join(f"{sha256(path)}  {path.name}" for path in sorted(written)) + "\n",
        encoding="ascii",
    )

    print(f"Scored {len(rows)} candidates")
    for name, count in sorted(Counter(row["recommendation"] for row in rows).items()):
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
