"""Create an explicit AI-assisted review of the 52 low-frequency candidates."""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data_sources/processed/extension_hold_without_more_evidence.csv"
DEFAULT_OUTPUT = ROOT / "data_sources/processed"

FIELDS = [
    "word",
    "bnc_rank",
    "contemporary_rank",
    "relevance_score",
    "oewn_pos",
    "form_review_flags",
    "review_decision",
    "preferred_headword",
    "educational_theme",
    "decision_reason",
    "review_method",
    "review_status",
]


# This table is intentionally explicit rather than hidden in a numerical formula.
# Each judgment can therefore be challenged or changed without altering raw data.
DECISIONS: dict[str, tuple[str, str, str, str]] = {
    "addicted": ("promote_to_secondary_review", "", "人与自我", "健康、习惯与社会问题阅读中有明确价值"),
    "airmail": ("retain_on_hold", "", "人与社会", "邮政义项明确，但现代使用场景减少且频率支持较弱"),
    "backache": ("promote_to_secondary_review", "", "人与自我", "健康与身体主题中的常用症状词"),
    "ballpoint": ("promote_to_secondary_review", "", "人与社会", "学习用品和日常物品主题中有实用价值"),
    "barbershop": ("promote_to_secondary_review", "", "人与社会", "社区生活和服务场景中有明确价值"),
    "bedclothes": ("merge_with_preferred_headword", "bedding", "人与自我", "与更通用的集合词 bedding 高度重合，避免重复收词"),
    "birdcage": ("retain_on_hold", "", "人与自然", "词义明确但属于透明复合词，独立学习收益有限"),
    "bookmark": ("promote_to_secondary_review", "", "人与社会", "纸质阅读和数字阅读场景均常用"),
    "centigrade": ("promote_to_secondary_review", "", "人与自然", "温度和科学阅读中仍需识别，后续应与 Celsius 建立变体关系"),
    "changeable": ("retain_on_hold", "", "一般阅读", "词义常见但可由 change 规则派生，独立收录价值需控制"),
    "customs": ("promote_to_secondary_review", "", "人与社会", "作为海关和关税的独立集合名词，不按 custom 的普通复数处理"),
    "dictation": ("promote_to_secondary_review", "", "人与社会", "学校学习和语言教学场景中有明确价值"),
    "eastwards": ("promote_to_secondary_review", "", "人与自然", "方向和地理阅读中实用，后续与 eastward 建立词形关系"),
    "eggplant": ("promote_to_secondary_review", "", "人与自然", "食物、植物及美式英语阅读中常见"),
    "firework": ("promote_to_secondary_review", "", "人与社会", "节庆、文化和安全主题中常见"),
    "franc": ("retain_on_hold", "", "人与社会", "主要用于历史货币语境，现代通用学习价值有限"),
    "gallon": ("promote_to_secondary_review", "", "人与自然", "英美计量单位，说明文和生活阅读中需要识别"),
    "glasshouse": ("merge_with_preferred_headword", "greenhouse", "人与自然", "与课标词 greenhouse 同义度高，优先保留课标词头"),
    "greengrocer": ("retain_on_hold", "", "人与社会", "英式地域色彩和透明复合结构较强，需控制扩展规模"),
    "gruel": ("retain_on_hold", "", "人与自我", "多见于历史或文学饮食语境，现代频率和适用面有限"),
    "hardworking": ("promote_to_secondary_review", "", "人与自我", "人物品质描述中常见，OEWN确认当前拼写为独立词头"),
    "hibernate": ("promote_to_secondary_review", "", "人与自然", "动物、生物与科技休眠语境均有价值"),
    "hooray": ("retain_on_hold", "", "人与社会", "口语感叹用法明确，但不宜由名词频率直接决定收录"),
    "latest": ("promote_to_secondary_review", "", "一般阅读", "除规则最高级外还有“最新消息/最新的”词汇化用法"),
    "litre": ("promote_to_secondary_review", "", "人与自然", "公制容量单位及英式拼写，说明文中实用"),
    "miniskirt": ("retain_on_hold", "", "人与社会", "服饰词义明确，但主题覆盖和阅读必要性有限"),
    "motherland": ("promote_to_secondary_review", "", "人与社会", "国家、文化与身份主题阅读中有价值"),
    "necktie": ("merge_with_preferred_headword", "tie", "人与社会", "课标词 tie 已覆盖核心物品义，避免同义重复扩张"),
    "northwards": ("promote_to_secondary_review", "", "人与自然", "方向和地理阅读中实用，后续与 northward 建立词形关系"),
    "oilfield": ("promote_to_secondary_review", "", "人与自然", "能源、资源和环境主题中的常见复合词"),
    "ox": ("promote_to_secondary_review", "", "人与自然", "动物、农业和文化阅读中的基础名词"),
    "playroom": ("retain_on_hold", "", "人与社会", "透明复合词，独立收录收益有限"),
    "postbox": ("retain_on_hold", "", "人与社会", "英式邮政词，现代覆盖有限且可与 mailbox 对照处理"),
    "postcode": ("promote_to_secondary_review", "", "人与社会", "地址、邮政和英式生活场景中实用"),
    "punctual": ("promote_to_secondary_review", "", "人与自我", "时间管理和人物品质主题中的常用形容词"),
    "rewind": ("promote_to_secondary_review", "", "人与社会", "媒体操作及比喻性表达中仍有识别价值"),
    "salesgirl": ("exclude_dated_or_gendered", "salesperson", "人与社会", "带不必要的性别限定且现代用法趋于过时，不纳入通用学习词头"),
    "scores": ("merge_with_preferred_headword", "score", "一般阅读", "课标词 score 已覆盖词头；旧复数形式不另建扩展记录"),
    "seashell": ("promote_to_secondary_review", "", "人与自然", "海洋、生物和自然观察主题中有明确价值"),
    "secondhand": ("promote_to_secondary_review", "", "人与社会", "消费、环保和信息来源语境均常用"),
    "shaver": ("retain_on_hold", "", "人与自我", "日用品词义明确但属于透明派生词，独立学习收益有限"),
    "skillful": ("promote_to_secondary_review", "", "人与自我", "能力和表现描述中常用，需与英式拼写 skilful 对照"),
    "skillfully": ("merge_with_preferred_headword", "skillful", "人与自我", "规则副词派生，优先在 skillful 词族中呈现"),
    "sneaker": ("promote_to_secondary_review", "", "人与社会", "服饰、运动和美式英语生活场景中常见"),
    "softball": ("promote_to_secondary_review", "", "人与社会", "体育和跨文化阅读中的常见运动名词"),
    "stopwatch": ("promote_to_secondary_review", "", "人与社会", "体育计时和实验测量场景中实用"),
    "subtraction": ("promote_to_secondary_review", "", "人与自然", "数学学科阅读中的基础术语"),
    "sunburnt": ("retain_on_hold", "", "人与自我", "英式分词形容词，宜先与 sunburn/sunburned 统一词族"),
    "sunglasses": ("promote_to_secondary_review", "", "人与自我", "虽为固定复数形式，但属于常见生活和健康词"),
    "superman": ("move_to_special_reference_review", "", "人与社会", "普通名词、角色专名及俚语义可能混淆，不进普通扩展表"),
    "windbreaker": ("promote_to_secondary_review", "", "人与社会", "服饰和天气场景中具有实际阅读价值"),
    "workday": ("promote_to_secondary_review", "", "人与社会", "工作制度和日常生活阅读中的常用复合词"),
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_report(path: Path, rows: list[dict[str, object]]) -> None:
    counts = Counter(str(row["review_decision"]) for row in rows)
    lines = [
        "# 52个低频暂缓词逐词复核报告",
        "",
        "## 复核方法",
        "",
        "本轮是AI辅助的逐词语义复核，不冒充人工专家审核。依据包括 OEWN 独立词头和义项、BNC/当代语料排名、是否与课标词重复、词形规范性以及高中常见阅读主题。没有使用旧中文释义、旧音标或 ECDICT 的考试标签决定结果。",
        "",
        "## 结果",
        "",
        "| 建议 | 数量 |",
        "| --- | ---: |",
    ]
    for decision in sorted(counts):
        lines.append(f"| {decision} | {counts[decision]} |")
    lines.extend(
        [
            "",
            "`promote_to_secondary_review` 只表示从低频暂缓区移入二次候选，不代表已经进入最终发布词库。合并、排除和特殊条目建议均保留原词及理由，以便追溯。",
            "",
            "## 后续",
            "",
            "将升入二次候选的词与原中档候选合并，再统一检查主题覆盖、英美变体和词族冗余。其余暂缓词只有获得新的独立证据时才重新考虑。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    source = read_rows(args.input)
    source_words = {row["legacy_word"] for row in source}
    if source_words != set(DECISIONS):
        raise RuntimeError(
            f"Decision table mismatch; missing={sorted(source_words - set(DECISIONS))}, "
            f"extra={sorted(set(DECISIONS) - source_words)}"
        )
    rows: list[dict[str, object]] = []
    for row in source:
        word = row["legacy_word"]
        decision, preferred, theme, reason = DECISIONS[word]
        rows.append(
            {
                "word": word,
                "bnc_rank": row["bnc_rank"],
                "contemporary_rank": row["contemporary_rank"],
                "relevance_score": row["relevance_score"],
                "oewn_pos": row["oewn_pos"],
                "form_review_flags": row["form_review_flags"],
                "review_decision": decision,
                "preferred_headword": preferred,
                "educational_theme": theme,
                "decision_reason": reason,
                "review_method": "ai_assisted_explicit_semantic_review",
                "review_status": "documented_recommendation",
            }
        )
    rows.sort(key=lambda row: str(row["word"]).casefold())

    args.output_dir.mkdir(parents=True, exist_ok=True)
    groups = {
        "extension_hold_review_all.csv": rows,
        "extension_hold_promoted_to_secondary.csv": [
            row for row in rows if row["review_decision"] == "promote_to_secondary_review"
        ],
        "extension_hold_still_on_hold.csv": [
            row for row in rows if row["review_decision"] == "retain_on_hold"
        ],
        "extension_hold_merge_exclude_special.csv": [
            row
            for row in rows
            if row["review_decision"]
            not in {"promote_to_secondary_review", "retain_on_hold"}
        ],
    }
    written: list[Path] = []
    for filename, group in groups.items():
        path = args.output_dir / filename
        write_rows(path, group)
        written.append(path)
    report = args.output_dir / "extension_hold_review_report.md"
    write_report(report, rows)
    written.append(report)
    checksums = args.output_dir / "extension_hold_review_SHA256SUMS.txt"
    checksums.write_text(
        "\n".join(f"{sha256(path)}  {path.name}" for path in sorted(written)) + "\n",
        encoding="ascii",
    )

    print(f"Reviewed {len(rows)} hold candidates")
    for decision, count in sorted(Counter(row["review_decision"] for row in rows).items()):
        print(f"  {decision}: {count}")


if __name__ == "__main__":
    main()
