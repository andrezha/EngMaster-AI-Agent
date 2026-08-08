"""Extract Appendix 2 from the archived 2020 senior-high English standard.

This is a development/data-governance utility. It is not used by the packaged
application. Install its only dependency with:

    python -m pip install pypdf
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover - developer guidance
    raise SystemExit("Missing dependency: install pypdf before running this tool") from exc


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data_sources" / "raw" / "moe"
OUTPUT_DIR = ROOT / "data_sources" / "processed"
PDF_GLOB = "*.pdf"
SOURCE_ID = "moe-hs-english-2017-2020-appendix-2"

EXPECTED_TOTAL = 3000
DECLARED_LEVEL_COUNTS = {
    "compulsory_education": 1500,
    "high_school_compulsory": 500,
    "high_school_selective_compulsory": 1000,
}

LEVEL_BY_MARKER = {
    "": "compulsory_education",
    "*": "high_school_compulsory",
    "**": "high_school_selective_compulsory",
}


def compact_whitespace(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").strip().split())


def contains_cjk(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_archived_pdf() -> Path:
    files = sorted(RAW_DIR.glob(PDF_GLOB))
    if len(files) != 1:
        raise SystemExit(
            f"Expected exactly one archived PDF in {RAW_DIR}, found {len(files)}"
        )
    return files[0]


def classify_form(headword: str) -> str:
    if " " in headword:
        return "multiword"
    if "-" in headword:
        return "hyphenated"
    if re.fullmatch(r"[A-Z][A-Z0-9.]*", headword):
        return "abbreviation_or_uppercase"
    return "word"


def split_entry(raw_entry: str) -> dict[str, str]:
    marker_match = re.search(r"(\*{1,2})$", raw_entry)
    marker = marker_match.group(1) if marker_match else ""
    entry = raw_entry[: -len(marker)].rstrip() if marker else raw_entry

    note_match = re.fullmatch(r"(.+?)\s*\((.+)\)", entry)
    if note_match:
        headword = note_match.group(1).strip()
        parenthetical_note = note_match.group(2).strip()
    else:
        headword = entry
        parenthetical_note = ""

    return {
        "entry": entry,
        "headword": headword,
        "parenthetical_note": parenthetical_note,
        "marker": marker,
        "curriculum_level": LEVEL_BY_MARKER[marker],
        "form_type": classify_form(headword),
    }


def extract_rows(pdf_path: Path) -> list[dict[str, object]]:
    reader = PdfReader(pdf_path)
    rows: list[dict[str, object]] = []
    collecting = False
    current_section = ""
    pending_entry: tuple[str, int, int | None] | None = None

    # The archived file has Appendix 2 on zero-based PDF indexes 128 onward.
    # Stop at the final lexical entry ("zoo") before the separate country table.
    for page_index in range(128, min(186, len(reader.pages))):
        text = reader.pages[page_index].extract_text() or ""
        lines = [compact_whitespace(line) for line in text.splitlines()]
        print_page = next(
            (
                int(line)
                for line in lines
                if re.fullmatch(r"\d{3}", line) and 121 <= int(line) <= 178
            ),
            None,
        )

        for line in lines:
            if not collecting:
                if line == "A":
                    collecting = True
                    current_section = "A"
                continue

            if not line or re.fullmatch(r"\d+", line) or contains_cjk(line):
                continue

            # A single capital letter normally starts an alphabetic section.
            # The second consecutive "I" is the pronoun entry itself.
            if re.fullmatch(r"[A-Z]", line):
                if line != current_section:
                    current_section = line
                    continue

            if not re.search(r"[A-Za-z]", line):
                continue

            entry_pdf_page = page_index + 1
            entry_print_page = print_page
            if pending_entry is not None:
                pending_text, entry_pdf_page, entry_print_page = pending_entry
                line = compact_whitespace(f"{pending_text} {line}")
                pending_entry = None

            # One source entry (kilo) wraps inside its parenthetical spelling
            # variant. Join any generally unbalanced parenthetical entry before
            # interpreting its marker or counting it as a separate row.
            if line.count("(") > line.count(")"):
                pending_entry = (line, entry_pdf_page, entry_print_page)
                continue

            parsed = split_entry(line)
            rows.append(
                {
                    "sequence": len(rows) + 1,
                    "raw_entry": line,
                    **parsed,
                    "alphabetic_section": current_section,
                    "source_pdf_page": entry_pdf_page,
                    "source_print_page": entry_print_page,
                    "source_id": SOURCE_ID,
                }
            )

            if parsed["entry"] == "zoo":
                return rows

    raise RuntimeError("Did not find the final Appendix 2 entry: zoo")


def validate(rows: list[dict[str, object]]) -> dict[str, object]:
    level_counts = Counter(str(row["curriculum_level"]) for row in rows)
    duplicate_entries = sorted(
        entry
        for entry, count in Counter(str(row["entry"]) for row in rows).items()
        if count > 1
    )

    errors: list[str] = []
    warnings: list[str] = []
    if len(rows) != EXPECTED_TOTAL:
        errors.append(f"expected {EXPECTED_TOTAL} entries, extracted {len(rows)}")
    if dict(level_counts) != DECLARED_LEVEL_COUNTS:
        warnings.append(
            f"printed marker counts {dict(level_counts)} differ from the "
            f"document's declared counts {DECLARED_LEVEL_COUNTS}; preserve "
            "the printed markers pending authoritative clarification"
        )
    if duplicate_entries:
        errors.append(f"duplicate entries: {duplicate_entries}")

    sequence_ok = all(
        int(row["sequence"]) == index for index, row in enumerate(rows, start=1)
    )
    if not sequence_ok:
        errors.append("sequence numbers are not contiguous")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "total": len(rows),
        "level_counts": dict(level_counts),
        "marker_counts": dict(Counter(str(row["marker"]) for row in rows)),
        "form_type_counts": dict(Counter(str(row["form_type"]) for row in rows)),
        "parenthetical_entry_count": sum(
            bool(row["parenthetical_note"]) for row in rows
        ),
        "slash_entry_count": sum("/" in str(row["entry"]) for row in rows),
        "duplicate_entries": duplicate_entries,
        "first_entry": rows[0]["entry"] if rows else None,
        "last_entry": rows[-1]["entry"] if rows else None,
    }


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    fieldnames = [
        "sequence",
        "raw_entry",
        "entry",
        "headword",
        "parenthetical_note",
        "marker",
        "curriculum_level",
        "form_type",
        "alphabetic_section",
        "source_pdf_page",
        "source_print_page",
        "source_id",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(rows: list[dict[str, object]], path: Path) -> None:
    path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_report(
    validation: dict[str, object], pdf_path: Path, output_hashes: dict[str, str]
) -> None:
    levels = validation["level_counts"]
    forms = validation["form_type_counts"]
    report = f"""# 教育部高中英语课标附录2提取报告

生成工具：`tools/extract_moe_curriculum_vocab.py`  
数据源标识：`{SOURCE_ID}`

## 提取结论

- 校验状态：{'通过' if validation['valid'] else '失败'}
- 词条总数：{validation['total']}
- 义务教育阶段（无星号）：{levels.get('compulsory_education', 0)}
- 高中必修（一个星号）：{levels.get('high_school_compulsory', 0)}
- 高中选择性必修（两个星号）：{levels.get('high_school_selective_compulsory', 0)}
- 首词条：`{validation['first_entry']}`
- 末词条：`{validation['last_entry']}`
- 重复完整词条：{len(validation['duplicate_entries'])}
- 带括号说明或变体的词条：{validation['parenthetical_entry_count']}
- 原文中含 `/` 的词条：{validation['slash_entry_count']}

## 形式统计

- 单一词形：{forms.get('word', 0)}
- 多词形式：{forms.get('multiword', 0)}
- 连字符形式：{forms.get('hyphenated', 0)}
- 缩写或全大写形式：{forms.get('abbreviation_or_uppercase', 0)}

`form_type` 是后续清洗提示，不改变教育部附录中的原始词条。

## 原文件内部不一致

附录说明声明：无星号1500词、一个星号500词、两个星号1000词。
对正式PDF逐条统计得到：无星号1500词、一个星号499词、两个星号1001词。

昌都市教育局与人民教育出版社公开的两份PDF具有完全相同的文件大小和
SHA-256，因此这不是本次下载损坏或不同镜像版本造成的差异。母表保留
PDF实际印刷的星号，不擅自把某个二星词改为一星词；该项作为来源文件
内部不一致继续留档。

## 文件校验

- 原始PDF SHA-256：`{sha256_file(pdf_path)}`
- CSV SHA-256：`{output_hashes['csv']}`
- JSON SHA-256：`{output_hashes['json']}`

## 解析边界

- 从附录2的字母 `A` 后开始采集。
- 在词汇表末词 `zoo` 处停止。
- 不将后续“主要国家名称及相关信息（供教学参考）”表格计入3000词母表。
- 保留原始星号、括号、美式拼写说明和多词形式，不擅自拆分。
"""
    (OUTPUT_DIR / "curriculum_vocabulary_report.md").write_text(
        report, encoding="utf-8"
    )


def main() -> int:
    pdf_path = find_archived_pdf()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = extract_rows(pdf_path)
    validation = validate(rows)

    csv_path = OUTPUT_DIR / "curriculum_vocabulary.csv"
    json_path = OUTPUT_DIR / "curriculum_vocabulary.json"
    write_csv(rows, csv_path)
    write_json(rows, json_path)

    output_hashes = {
        "csv": sha256_file(csv_path),
        "json": sha256_file(json_path),
    }
    (OUTPUT_DIR / "SHA256SUMS.txt").write_text(
        f"{output_hashes['csv']}  {csv_path.name}\n"
        f"{output_hashes['json']}  {json_path.name}\n",
        encoding="utf-8",
    )
    write_report(validation, pdf_path, output_hashes)

    print(json.dumps(validation, ensure_ascii=False, indent=2))
    if not validation["valid"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
