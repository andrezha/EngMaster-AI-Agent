"""Match the legacy vocabulary index to the archived MOE Appendix 2 master.

The script is deliberately read-only with respect to ``assets/vocabulary.json``.
It creates audit artifacts under ``data_sources/processed`` and never copies the
legacy Chinese definitions into those artifacts.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
LEGACY_PATH = ROOT / "assets" / "vocabulary.json"
CURRICULUM_PATH = (
    ROOT / "data_sources" / "processed" / "curriculum_vocabulary.json"
)
OUTPUT_DIR = ROOT / "data_sources" / "processed"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_key(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = value.replace("’", "'").replace("‘", "'")
    return " ".join(value.strip().split())


def folded_key(value: str) -> str:
    return display_key(value).casefold()


def loose_key(value: str) -> str:
    # Used only after literal and case-normalized matching. Removing these
    # separators handles forms such as ice-cream/ice cream and email/e-mail.
    # Case is deliberately preserved so that Miss. cannot collapse into miss,
    # and No. cannot be treated automatically as the word no.
    return re.sub(r"[\s\-.'’]", "", display_key(value))


def add_alias(
    aliases: list[dict[str, object]],
    seen: set[tuple[int, str]],
    row: dict[str, object],
    alias: str,
    alias_type: str,
) -> None:
    alias = display_key(alias.strip(" ,"))
    if not alias or not re.search(r"[A-Za-z]", alias):
        return
    identity = (int(row["sequence"]), alias)
    if identity in seen:
        return
    seen.add(identity)
    aliases.append(
        {
            "curriculum_sequence": int(row["sequence"]),
            "curriculum_entry": str(row["entry"]),
            "curriculum_level": str(row["curriculum_level"]),
            "alias": alias,
            "alias_type": alias_type,
            "source_print_page": int(row["source_print_page"]),
        }
    )


def build_aliases(curriculum: list[dict[str, object]]) -> list[dict[str, object]]:
    aliases: list[dict[str, object]] = []
    seen: set[tuple[int, str]] = set()

    for row in curriculum:
        headword = display_key(str(row["headword"]))
        add_alias(aliases, seen, row, headword, "primary")

        if "/" in headword:
            for component in headword.split("/"):
                add_alias(aliases, seen, row, component, "slash_component")

        note = display_key(str(row.get("parenthetical_note", "")))
        if not note:
            continue

        if note == "s":
            add_alias(aliases, seen, row, headword + "s", "suffix_variant")
            continue

        if note.casefold().startswith("pl. "):
            note = note[4:].strip()
            alias_type = "inflection_variant"
        else:
            alias_type = "parenthetical_variant"

        for variant in re.split(r"\s*[,/]\s*", note):
            add_alias(aliases, seen, row, variant, alias_type)

    return aliases


def index_aliases(
    aliases: Iterable[dict[str, object]], key_function
) -> dict[str, list[dict[str, object]]]:
    index: dict[str, list[dict[str, object]]] = defaultdict(list)
    for alias in aliases:
        index[key_function(str(alias["alias"]))].append(alias)
    return dict(index)


def choose_candidate(
    candidates: list[dict[str, object]],
) -> tuple[dict[str, object] | None, str]:
    if not candidates:
        return None, "none"

    # Prefer an official primary spelling over a variant that happens to equal
    # another official headword (for example disc versus disk (disc)).
    primary = [candidate for candidate in candidates if candidate["alias_type"] == "primary"]
    primary_sequences = {int(candidate["curriculum_sequence"]) for candidate in primary}
    if len(primary_sequences) == 1:
        return primary[0], "primary_preferred"

    sequences = {int(candidate["curriculum_sequence"]) for candidate in candidates}
    if len(sequences) == 1:
        return candidates[0], "unique_entry"
    return None, "ambiguous"


def match_word(
    word: str,
    literal_index: dict[str, list[dict[str, object]]],
    folded_index: dict[str, list[dict[str, object]]],
    loose_index: dict[str, list[dict[str, object]]],
) -> dict[str, object]:
    stages = [
        ("literal", display_key(word), literal_index),
        ("case_normalized", folded_key(word), folded_index),
        ("orthographic_normalized", loose_key(word), loose_index),
    ]

    for stage, key, index in stages:
        candidates = index.get(key, [])
        if not candidates:
            continue
        candidate, resolution = choose_candidate(candidates)
        if candidate is None:
            return {
                "match_status": "ambiguous",
                "match_stage": stage,
                "matched_curriculum_sequence": "",
                "matched_curriculum_entry": "",
                "matched_alias": "",
                "alias_type": "",
                "curriculum_level": "",
                "requires_review": "yes",
                "match_note": "; ".join(
                    f"{item['curriculum_sequence']}:{item['curriculum_entry']}"
                    for item in candidates
                ),
            }

        alias_type = str(candidate["alias_type"])
        if stage == "literal" and alias_type == "primary":
            status = "exact_primary"
        elif stage == "literal":
            status = "exact_official_variant"
        elif stage == "case_normalized":
            status = "case_normalized"
        else:
            status = "orthographic_normalized"

        return {
            "match_status": status,
            "match_stage": stage,
            "matched_curriculum_sequence": candidate["curriculum_sequence"],
            "matched_curriculum_entry": candidate["curriculum_entry"],
            "matched_alias": candidate["alias"],
            "alias_type": alias_type,
            "curriculum_level": candidate["curriculum_level"],
            "requires_review": "yes" if stage == "orthographic_normalized" else "no",
            "match_note": resolution,
        }

    return {
        "match_status": "unmatched_extension_candidate",
        "match_stage": "none",
        "matched_curriculum_sequence": "",
        "matched_curriculum_entry": "",
        "matched_alias": "",
        "alias_type": "",
        "curriculum_level": "",
        "requires_review": "yes",
        "match_note": "not found in official entry aliases",
    }


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    legacy = json.loads(LEGACY_PATH.read_text(encoding="utf-8"))
    curriculum = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
    if not isinstance(legacy, list) or not isinstance(curriculum, list):
        raise SystemExit("Expected both source files to contain JSON arrays")

    aliases = build_aliases(curriculum)
    literal_index = index_aliases(aliases, display_key)
    folded_index = index_aliases(aliases, folded_key)
    loose_index = index_aliases(aliases, loose_key)

    mapping: list[dict[str, object]] = []
    for row_index, legacy_row in enumerate(legacy, start=1):
        word = str(legacy_row.get("word", ""))
        result = match_word(word, literal_index, folded_index, loose_index)
        mapping.append(
            {
                "legacy_row": row_index,
                "legacy_word": word,
                **result,
            }
        )

    confirmed_matched = [
        row
        for row in mapping
        if row["match_status"]
        not in {
            "unmatched_extension_candidate",
            "ambiguous",
            "orthographic_normalized",
        }
    ]
    provisional_matched = [
        row for row in mapping if row["match_status"] == "orthographic_normalized"
    ]
    confirmed_covered_sequences = {
        int(row["matched_curriculum_sequence"])
        for row in confirmed_matched
        if row["matched_curriculum_sequence"] != ""
    }
    provisional_covered_sequences = {
        int(row["matched_curriculum_sequence"])
        for row in provisional_matched
        if row["matched_curriculum_sequence"] != ""
    } - confirmed_covered_sequences
    missing = [
        row
        for row in curriculum
        if int(row["sequence"]) not in confirmed_covered_sequences
    ]
    provisional_coverage = [
        row
        for row in provisional_matched
        if int(row["matched_curriculum_sequence"])
        in provisional_covered_sequences
    ]
    provisional_by_sequence: dict[int, list[str]] = defaultdict(list)
    for row in provisional_coverage:
        provisional_by_sequence[int(row["matched_curriculum_sequence"])].append(
            str(row["legacy_word"])
        )
    missing_audit = [
        {
            **row,
            "coverage_status": (
                "provisional_orthographic_match"
                if int(row["sequence"]) in provisional_by_sequence
                else "not_covered"
            ),
            "provisional_legacy_words": ";".join(
                provisional_by_sequence.get(int(row["sequence"]), [])
            ),
        }
        for row in missing
    ]

    extension_groups: dict[str, list[int]] = defaultdict(list)
    for row in mapping:
        if row["match_status"] == "unmatched_extension_candidate":
            extension_groups[str(row["legacy_word"])].append(int(row["legacy_row"]))
    extensions = [
        {
            "legacy_word": word,
            "legacy_row_count": len(indexes),
            "legacy_rows": ";".join(map(str, indexes)),
            "classification": "extension_candidate_pending_review",
        }
        for word, indexes in sorted(extension_groups.items(), key=lambda item: item[0].casefold())
    ]

    all_word_groups: dict[str, list[int]] = defaultdict(list)
    for row_index, legacy_row in enumerate(legacy, start=1):
        all_word_groups[str(legacy_row.get("word", ""))].append(row_index)
    duplicates = [
        {
            "legacy_word": word,
            "row_count": len(indexes),
            "legacy_rows": ";".join(map(str, indexes)),
        }
        for word, indexes in sorted(all_word_groups.items(), key=lambda item: item[0].casefold())
        if len(indexes) > 1
    ]

    ambiguous = [row for row in mapping if row["match_status"] == "ambiguous"]
    status_counts = Counter(str(row["match_status"]) for row in mapping)
    unique_words = {str(row.get("word", "")) for row in legacy}
    confirmed_matched_unique_words = {
        str(row["legacy_word"])
        for row in mapping
        if row["match_status"]
        not in {
            "unmatched_extension_candidate",
            "ambiguous",
            "orthographic_normalized",
        }
    }
    missing_level_counts = Counter(str(row["curriculum_level"]) for row in missing)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_paths = {
        "mapping": OUTPUT_DIR / "current_vocab_curriculum_mapping.csv",
        "missing": OUTPUT_DIR / "curriculum_missing_from_current.csv",
        "extensions": OUTPUT_DIR / "current_vocab_extension_candidates.csv",
        "duplicates": OUTPUT_DIR / "current_vocab_duplicate_groups.csv",
        "aliases": OUTPUT_DIR / "curriculum_match_aliases.csv",
        "provisional": OUTPUT_DIR / "curriculum_provisional_orthographic_matches.csv",
    }

    write_csv(
        output_paths["mapping"],
        mapping,
        [
            "legacy_row",
            "legacy_word",
            "match_status",
            "match_stage",
            "matched_curriculum_sequence",
            "matched_curriculum_entry",
            "matched_alias",
            "alias_type",
            "curriculum_level",
            "requires_review",
            "match_note",
        ],
    )
    write_csv(
        output_paths["missing"],
        missing_audit,
        list(curriculum[0].keys())
        + ["coverage_status", "provisional_legacy_words"],
    )
    write_csv(
        output_paths["extensions"],
        extensions,
        ["legacy_word", "legacy_row_count", "legacy_rows", "classification"],
    )
    write_csv(
        output_paths["duplicates"],
        duplicates,
        ["legacy_word", "row_count", "legacy_rows"],
    )
    write_csv(
        output_paths["aliases"],
        aliases,
        [
            "curriculum_sequence",
            "curriculum_entry",
            "curriculum_level",
            "alias",
            "alias_type",
            "source_print_page",
        ],
    )
    write_csv(
        output_paths["provisional"],
        provisional_coverage,
        [
            "legacy_row",
            "legacy_word",
            "match_status",
            "match_stage",
            "matched_curriculum_sequence",
            "matched_curriculum_entry",
            "matched_alias",
            "alias_type",
            "curriculum_level",
            "requires_review",
            "match_note",
        ],
    )

    output_hashes = {name: sha256_file(path) for name, path in output_paths.items()}
    (OUTPUT_DIR / "matching_SHA256SUMS.txt").write_text(
        "".join(
            f"{output_hashes[name]}  {path.name}\n"
            for name, path in output_paths.items()
        ),
        encoding="utf-8",
    )

    report = f"""# 现有词库与教育部课标附录2匹配报告

生成工具：`tools/match_existing_vocab_to_curriculum.py`

## 数据范围

- 现有词库行数：{len(legacy)}
- 现有词库精确唯一词形：{len(unique_words)}
- 官方课标母表词条：{len(curriculum)}
- 匹配别名总数：{len(aliases)}
- 现有重复词组数：{len(duplicates)}

本报告只使用现有词库的 `word` 字段，不复制或输出旧中文释义、音标和例句。

## 现有词库匹配结果（按行）

- 官方主词精确匹配：{status_counts.get('exact_primary', 0)}
- 官方括号、复数或斜杠变体匹配：{status_counts.get('exact_official_variant', 0)}
- 仅大小写规范化后匹配：{status_counts.get('case_normalized', 0)}
- 连字符、空格或标点规范化后匹配：{status_counts.get('orthographic_normalized', 0)}
- 大小写或别名冲突，需确认：{status_counts.get('ambiguous', 0)}
- 未进入官方3000词，列为拓展候选：{status_counts.get('unmatched_extension_candidate', 0)}
- 已确认匹配的唯一现有词形：{len(confirmed_matched_unique_words)} / {len(unique_words)}
- 仅标点、空格或连字符近似，暂不计入确认覆盖：{len(provisional_matched)}

## 官方母表覆盖结果

- 已被现有词库主词或官方变体确认覆盖：{len(confirmed_covered_sequences)} / {len(curriculum)}
- 仅被正字法近似形式暂定覆盖：{len(provisional_covered_sequences)}
- 现有词库尚未覆盖：{len(missing)}
- 上述缺失项中存在正字法暂定匹配：{len(provisional_covered_sequences)}
- 缺失项中义务教育层：{missing_level_counts.get('compulsory_education', 0)}
- 缺失项中高中必修层：{missing_level_counts.get('high_school_compulsory', 0)}
- 缺失项中选择性必修层：{missing_level_counts.get('high_school_selective_compulsory', 0)}

## 匹配规则

1. 优先匹配官方主词的大小写和标点原形。
2. 其次匹配官方括号中的美式拼写、简称、复数，以及 `/` 两侧词形。
3. 再进行唯一的大小写规范化匹配；`US/us`、`China/china` 等不会强行合并。
4. 最后在保持大小写的前提下允许连字符、空格、句点和撇号规范化，所有此类结果标记为需复核。
5. 未匹配词只表示“课标外拓展候选”，不等于错误或必须删除。
6. 官方缺失词只表示当前 `word` 字段未覆盖，不代表旧释义中从未出现。

## 来源哈希

- `assets/vocabulary.json`：`{sha256_file(LEGACY_PATH)}`
- `curriculum_vocabulary.json`：`{sha256_file(CURRICULUM_PATH)}`

## 输出文件

- `current_vocab_curriculum_mapping.csv`：现有3876行逐行匹配结果。
- `curriculum_missing_from_current.csv`：官方母表尚未覆盖项。
- `current_vocab_extension_candidates.csv`：课标外候选，按词形去重。
- `current_vocab_duplicate_groups.csv`：现有重复词及行号。
- `curriculum_match_aliases.csv`：官方主词和变体匹配依据。
- `curriculum_provisional_orthographic_matches.csv`：标点、空格或连字符近似项，需人工或规则确认。
- `matching_SHA256SUMS.txt`：以上文件哈希。
"""
    report_path = OUTPUT_DIR / "current_vocab_curriculum_match_report.md"
    report_path.write_text(report, encoding="utf-8")

    summary = {
        "legacy_rows": len(legacy),
        "legacy_unique_words": len(unique_words),
        "curriculum_entries": len(curriculum),
        "status_counts": dict(status_counts),
        "confirmed_matched_unique_words": len(confirmed_matched_unique_words),
        "confirmed_covered_curriculum_entries": len(confirmed_covered_sequences),
        "provisional_orthographic_rows": len(provisional_matched),
        "provisional_covered_curriculum_entries": len(provisional_covered_sequences),
        "missing_curriculum_entries": len(missing),
        "extension_candidate_unique_words": len(extensions),
        "duplicate_groups": len(duplicates),
        "ambiguous_rows": len(ambiguous),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
