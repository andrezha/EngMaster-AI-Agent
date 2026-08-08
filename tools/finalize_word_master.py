"""Freeze the clean English headword scope and build the final word master."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data_sources/processed"
CLEAN = ROOT / "data_sources/clean"

EDGE_DECISIONS: dict[str, tuple[str, str]] = {
    "battleground": ("include", "社会、历史和新闻阅读中的常见复合名词"),
    "bodybuilding": ("include", "体育、健康和生活方式主题中的独立名词"),
    "bookshop": ("include", "学习和社区生活中的常见英式复合词"),
    "chips": ("include", "食物义为固定复数形式，不能简单还原为单数义"),
    "firefighter": ("include", "公共安全和职业主题中的现代中性称谓"),
    "founding": ("include", "历史、机构和社会主题中的词汇化名词"),
    "furnished": ("include", "住房和生活场景中的常用形容词"),
    "hey": ("include", "高频口语和对话阅读中的常用感叹词"),
    "judgement": ("include", "一般阅读中的常用名词及英式拼写"),
    "microcomputer": ("include", "科技史和计算机主题中仍需识别"),
    "nursing": ("include", "健康、职业和社会照护主题中的独立名词"),
    "oh": ("include", "高频对话和叙事文本中的常用感叹词"),
    "oneself": ("include", "语法和一般阅读中的常用反身代词"),
    "organiser": ("include", "活动和组织主题中的常用英式拼写"),
    "ouch": ("include", "对话和身体感受表达中的常用感叹词"),
    "ought": ("merge_into_curriculum_expression", "课标母表已原文收录 ought to，不重复建立扩展词头"),
    "pleased": ("include", "情感和交际主题中的词汇化形容词"),
    "seagull": ("include", "自然和海洋主题中的常见动物名词"),
    "sharpener": ("include", "学校用品主题中的常用派生名词"),
    "sightseeing": ("include", "旅行和文化主题中的词汇化名词"),
    "theirs": ("include", "语法和一般阅读中的常用物主代词"),
    "via": ("include", "高频路线、媒介和书面连接表达"),
    "videophone": ("exclude", "技术词已明显过时且独立频率较低"),
    "walkman": ("exclude", "来源涉及品牌化名称且设备已经过时，不进入通用主表"),
    "westwards": ("include", "方向和地理阅读中的有效英式词形"),
    "whichever": ("include", "语法和一般阅读中的常用限定词/代词"),
    "workforce": ("include", "经济、就业和社会主题中的高价值名词"),
    "workmate": ("include", "工作和人际关系主题中的常见英式名词"),
    "workplace": ("include", "就业、安全和社会主题中的高价值名词"),
    "yourselves": ("include", "语法和一般阅读中的固定反身代词形式"),
    "yummy": ("exclude", "口语色彩强且教育覆盖价值有限"),
}

SECONDARY_SPECIAL_DECISIONS: dict[str, tuple[str, str, str]] = {
    "airplane": ("merge_as_variant", "aeroplane", "与 aeroplane 为正字法变体，合并避免重复计数"),
    "businesswoman": ("exclude_gendered_occupation", "", "通用词表优先采用不限定性别的职业表达"),
    "headmistress": ("exclude_gendered_occupation", "", "通用词表优先采用 head teacher 等中性表达"),
    "hostess": ("exclude_gendered_occupation", "", "职业义带性别限定，移出通用主表"),
    "seaman": ("exclude_gendered_occupation", "", "通用学习词表优先采用 sailor/seafarer 等表达"),
    "statesman": ("exclude_gendered_occupation", "", "名称带性别限定，暂不进入通用主表"),
    "stewardess": ("exclude_gendered_occupation", "", "现代职业表达优先使用 flight attendant"),
    "waitress": ("exclude_gendered_occupation", "", "现代通用表达优先使用 server/waiter 等按语境处理"),
    "weatherman": ("exclude_gendered_occupation", "", "现代通用表达优先使用 weather presenter/meteorologist"),
}

MASTER_FIELDS = [
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean-dir", type=Path, default=CLEAN)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED)
    parser.add_argument("--output-dir", type=Path, default=CLEAN / "final_word_master")
    args = parser.parse_args()

    curriculum = json.loads((args.clean_dir / "curriculum_base.json").read_text(encoding="utf-8"))["records"]
    priority = read_csv(args.clean_dir / "extension_priority_draft/extension_priority_draft.csv")
    secondary = read_csv(args.clean_dir / "extension_secondary_review/extension_secondary_review_queue.csv")
    screening = read_csv(args.processed_dir / "extension_screening_all.csv")
    screen_by_word = {row["legacy_word"]: row for row in screening}

    edge_source = {
        row["legacy_word"]: row
        for row in screening
        if row["recommendation"] in {"modern_lexical_review", "legacy_lexicon_review"}
    }
    if set(edge_source) != set(EDGE_DECISIONS):
        raise RuntimeError("Lexical edge decision table does not match screened candidates")

    edge_audit: list[dict[str, object]] = []
    for word in sorted(edge_source, key=str.casefold):
        decision, reason = EDGE_DECISIONS[word]
        source = edge_source[word]
        edge_audit.append(
            {
                "word": word,
                "screening_bucket": source["recommendation"],
                "oewn_match_type": source["oewn_match_type"],
                "oewn_pos": source["oewn_pos"],
                "decision": decision,
                "reason": reason,
                "review_method": "ai_assisted_explicit_semantic_review",
            }
        )

    secondary_audit: list[dict[str, object]] = []
    secondary_kept: list[dict[str, str]] = []
    aliases: dict[str, list[str]] = {"aeroplane": ["airplane"]}
    for row in secondary:
        word = row["word"]
        special = SECONDARY_SPECIAL_DECISIONS.get(word)
        if special:
            decision, preferred, reason = special
        else:
            decision = "include"
            preferred = ""
            reason = "已通过中等频率或低频语义复核，并具有明确高中阅读主题价值"
            secondary_kept.append(row)
        secondary_audit.append(
            {
                "word": word,
                "queue_route": row["queue_route"],
                "relevance_score": row["relevance_score"],
                "decision": decision,
                "preferred_headword": preferred,
                "reason": reason,
            }
        )

    extensions: list[dict[str, object]] = []
    for row in priority:
        extensions.append(
            {
                "word": row["word"],
                "variants": "|".join(aliases.get(row["word"], [])),
                "part_of_speech": row["part_of_speech"],
                "theme_candidates": row["theme_candidates"],
                "selection_route": "strong_independent_frequency",
                "relevance_score": row["relevance_score"],
                "selection_reason": row["inclusion_reason"],
            }
        )
    for row in secondary_kept:
        extensions.append(
            {
                "word": row["word"],
                "variants": "|".join(aliases.get(row["word"], [])),
                "part_of_speech": row["part_of_speech"],
                "theme_candidates": row["theme_candidates"],
                "selection_route": row["queue_route"],
                "relevance_score": row["relevance_score"],
                "selection_reason": row["review_focus"],
            }
        )
    for row in edge_audit:
        if row["decision"] != "include":
            continue
        source = screen_by_word[str(row["word"])]
        extensions.append(
            {
                "word": row["word"],
                "variants": "",
                "part_of_speech": source["oewn_pos"],
                "theme_candidates": "一般阅读",
                "selection_route": "lexical_edge_semantic_review",
                "relevance_score": "",
                "selection_reason": row["reason"],
            }
        )

    extensions.sort(key=lambda row: str(row["word"]).casefold())
    extension_words = [str(row["word"]) for row in extensions]
    if len(extension_words) != len({word.casefold() for word in extension_words}):
        raise RuntimeError("Duplicate extension headword")

    curriculum_forms = {
        form.casefold()
        for row in curriculum
        for form in [row["word"], *row.get("official_variants", [])]
    }
    overlap = sorted({word.casefold() for word in extension_words} & curriculum_forms)
    if overlap:
        raise RuntimeError(f"Extension/curriculum overlap: {overlap[:10]}")

    master: list[dict[str, object]] = []
    for row in curriculum:
        master.append(
            {
                "word": row["word"],
                "variants": "|".join(row.get("official_variants", [])),
                "dataset_layer": "curriculum",
                "curriculum_level": row["curriculum_level"],
                "source_entry": row["source_entry"],
                "source_sequence": row["source_sequence"],
                "part_of_speech": "",
                "theme_candidates": "",
                "selection_route": "moe_curriculum_appendix_2",
                "relevance_score": "",
                "selection_reason": "教育部课程标准附录2原子词头",
            }
        )
    for row in extensions:
        master.append(
            {
                **row,
                "dataset_layer": "extension",
                "curriculum_level": "",
                "source_entry": "",
                "source_sequence": "",
            }
        )

    for index, row in enumerate(master, start=1):
        row.update(
            {
                "record_id": f"word-master-{index:04d}",
                "selection_status": "english_scope_frozen",
                "definitions_zh": "",
                "phonetic_uk": "",
                "phonetic_us": "",
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    master_csv = args.output_dir / "final_word_master.csv"
    write_csv(master_csv, MASTER_FIELDS, master)
    master_json = args.output_dir / "final_word_master.json"
    master_json.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dataset_id": "engmaster-final-english-word-master",
                "status": "english_scope_frozen",
                "record_count": len(master),
                "curriculum_record_count": len(curriculum),
                "extension_record_count": len(extensions),
                "records": master,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    edge_path = args.processed_dir / "extension_lexical_edge_final_decisions.csv"
    write_csv(
        edge_path,
        ["word", "screening_bucket", "oewn_match_type", "oewn_pos", "decision", "reason", "review_method"],
        edge_audit,
    )
    secondary_path = args.processed_dir / "extension_secondary_final_decisions.csv"
    write_csv(
        secondary_path,
        ["word", "queue_route", "relevance_score", "decision", "preferred_headword", "reason"],
        secondary_audit,
    )
    extension_path = args.output_dir / "final_extension_words.csv"
    extension_fields = [
        "word", "variants", "part_of_speech", "theme_candidates", "selection_route",
        "relevance_score", "selection_reason",
    ]
    write_csv(extension_path, extension_fields, extensions)

    excluded_path = args.output_dir / "excluded_or_separate_items.json"
    excluded_payload = {
        "secondary_not_in_main_word_table": [row for row in secondary_audit if row["decision"] != "include"],
        "lexical_edge_not_in_main_word_table": [row for row in edge_audit if row["decision"] != "include"],
        "structural_buckets_kept_separate": {
            "phrases": 63,
            "hyphenated_forms": 41,
            "proper_names_or_capitalized_forms": 43,
            "abbreviations": 8,
            "unverified_spellings": 2,
        },
    }
    excluded_path.write_text(json.dumps(excluded_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    route_counts = Counter(str(row["selection_route"]) for row in extensions)
    official_multiword_count = sum(any(char.isspace() for char in row["word"]) for row in curriculum)
    manifest_path = args.output_dir / "manifest.json"
    manifest = {
        "dataset_id": "engmaster-final-english-word-master",
        "status": "english_scope_frozen",
        "record_count": len(master),
        "curriculum_record_count": len(curriculum),
        "extension_record_count": len(extensions),
        "extension_route_counts": dict(route_counts),
        "definitions_and_phonetics_status": "intentionally_blank",
        "legacy_content_reused": False,
        "extra_phrases_hyphenated_proper_names_abbreviations_included": False,
        "official_curriculum_multiword_entries_preserved": official_multiword_count,
        "intentional_case_sensitive_pairs": [
            ["China", "china"],
            ["March", "march"],
            ["May", "may"],
            ["Miss", "miss"],
            ["US", "us"]
        ],
        "marketing_note": "Record count is the result of documented rules; it is not an official exam word count.",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readme_path = args.output_dir / "README.md"
    readme_path.write_text(
        "# 最终英文单词母表\n\n"
        f"本目录冻结了 {len(master)} 个英文词头：课标原子记录 {len(curriculum)} 个，独立筛选拓展词 {len(extensions)} 个。\n\n"
        "- 数量是规则筛选的自然结果，不宣称为教育部门发布的固定考试词数。\n"
        f"- 课标附录原有的 {official_multiword_count} 个多词条目按官方原文保留；除此之外，旧短语、连字符形式、额外专名和缩写未混入主表。\n"
        "- `China/china`、`March/march`、`May/may`、`Miss/miss`、`US/us` 是课标原文中需要区分的大小写词对，不作错误去重。\n"
        "- 旧词库的中文释义、音标、例句、顺序和编号均未继承。\n"
        "- 中文释义和英美音标字段目前有意留空，下一阶段再依据开放来源制作。\n"
        "- `selection_status=english_scope_frozen` 表示英文收词范围已冻结，不表示释义数据已经完成。\n",
        encoding="utf-8",
    )

    written = [master_csv, master_json, extension_path, excluded_path, manifest_path, readme_path]
    checksum_path = args.output_dir / "SHA256SUMS.txt"
    checksum_path.write_text(
        "\n".join(f"{sha256(path)}  {path.name}" for path in sorted(written)) + "\n",
        encoding="ascii",
    )

    print(f"Final master: {len(master)} records")
    print(f"  curriculum: {len(curriculum)}")
    print(f"  extension: {len(extensions)}")
    print(f"  secondary excluded/merged: {sum(row['decision'] != 'include' for row in secondary_audit)}")
    print(f"  lexical edge excluded: {sum(row['decision'] != 'include' for row in edge_audit)}")


if __name__ == "__main__":
    main()
