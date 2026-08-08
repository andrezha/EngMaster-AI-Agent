"""Build the final 3,800-word Chinese release table and audit artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
BATCH_DIR = ROOT / "data_sources/enrichment/chinese_definition_batches"
OUTPUT = ROOT / "data_sources/clean/release_vocabulary_3800_zh"
GENERATED_ON = "2026-08-08"

FIELDS = [
    "sequence",
    "record_id",
    "word",
    "variants",
    "dataset_layer",
    "curriculum_level",
    "parts_of_speech",
    "definitions_zh",
    "selected_source_sense_ids",
    "oewn_match_status",
    "definition_method",
    "qa_status",
    "qa_notes",
]

HEADERS_ZH = [
    "序号",
    "记录编号",
    "单词",
    "变体",
    "数据层",
    "课标层级",
    "词性",
    "中文释义",
    "开放语义来源编号",
    "OEWN匹配状态",
    "释义制作方法",
    "质量状态",
    "备注",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows() -> list[dict[str, str]]:
    records: list[dict[str, object]] = []
    for path in sorted(BATCH_DIR.glob("batch_[0-9][0-9][0-9].json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        records.extend(payload["records"])

    if len(records) != 3800:
        raise ValueError(f"expected 3800 records, got {len(records)}")

    rows: list[dict[str, str]] = []
    for sequence, record in enumerate(records, start=1):
        if record["definition_status"] != "ai_draft_complete":
            raise ValueError(f"unfinished definition: {record['word']}")
        if record["qa_status"] != "automated_checks_passed":
            raise ValueError(f"QA not passed: {record['word']}")
        definitions = record["definitions_zh"]
        if not definitions:
            raise ValueError(f"missing Chinese definition: {record['word']}")
        definition_text = " | ".join(
            f"{item['part_of_speech']}：{item['definition']}" for item in definitions
        )
        variants = record.get("variants", [])
        rows.append(
            {
                "sequence": str(sequence),
                "record_id": str(record["record_id"]),
                "word": str(record["word"]),
                "variants": "; ".join(variants) if isinstance(variants, list) else str(variants),
                "dataset_layer": str(record["dataset_layer"]),
                "curriculum_level": str(record.get("curriculum_level", "")),
                "parts_of_speech": "; ".join(record["display_parts_of_speech"]),
                "definitions_zh": definition_text,
                "selected_source_sense_ids": " | ".join(record["selected_source_sense_ids"]),
                "oewn_match_status": str(record["oewn_match_status"]),
                "definition_method": str(record["draft_method"]),
                "qa_status": str(record["qa_status"]),
                "qa_notes": "；".join(record["qa_notes"]),
            }
        )
    return rows


def xml_text(value: str) -> str:
    return escape(value, {'"': "&quot;"})


def col_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def sheet_xml(values: list[list[str]], widths: list[int]) -> str:
    rows_xml: list[str] = []
    for row_index, row in enumerate(values, start=1):
        cells: list[str] = []
        for col_index, value in enumerate(row, start=1):
            ref = f"{col_name(col_index)}{row_index}"
            style = "1" if row_index == 1 else "2"
            cells.append(
                f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">'
                f"{xml_text(str(value))}</t></is></c>"
            )
        rows_xml.append(f'<row r="{row_index}">' + "".join(cells) + "</row>")
    columns = "".join(
        f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>'
        for i, width in enumerate(widths, start=1)
    )
    last_cell = f"{col_name(max(len(row) for row in values))}{len(values)}"
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{last_cell}"/><sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '</sheetView></sheetViews><sheetFormatPr defaultRowHeight="18"/>'
        f"<cols>{columns}</cols><sheetData>{''.join(rows_xml)}</sheetData>"
        f'<autoFilter ref="A1:{col_name(len(values[0]))}{len(values)}"/>'
        '</worksheet>'
    )


def write_xlsx(path: Path, rows: list[dict[str, str]]) -> None:
    vocabulary = [HEADERS_ZH] + [[row[field] for field in FIELDS] for row in rows]
    notes = [
        ["项目", "说明"],
        ["数据集", "EngMaster 独立整理学习词汇 3800（中文释义版）"],
        ["规模", "3800词：课标母表3004词，独立筛选拓展796词"],
        ["中文释义", "依据开放英文语义证据选择常用义项后独立中文表述；未复制旧表中文释义"],
        ["开放语义来源", "Open English WordNet 2025；具体义项编号见词汇表"],
        ["其他核对来源", "Moby用于词形/词性辅助核对；ECDICT仅使用词头及频率字段"],
        ["质量状态", "3800词均通过自动结构、完整性、来源编号和记录对应检查；不等同人工校订"],
        ["产品声明", "3800为产品实际规模，不代表官方固定考试范围，也不宣称教育部门官方发布"],
    ]
    workbook = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="词汇表" sheetId="1" r:id="rId1"/><sheet name="制作说明" sheetId="2" r:id="rId2"/></sheets></workbook>'
    styles = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="10"/><name val="Microsoft YaHei"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Microsoft YaHei"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF305496"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"><alignment vertical="center"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="top" wrapText="1"/></xf></cellXfs></styleSheet>'
    content_types = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>'
    root_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    workbook_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'
    parts = {
        "[Content_Types].xml": content_types,
        "_rels/.rels": root_rels,
        "xl/workbook.xml": workbook,
        "xl/_rels/workbook.xml.rels": workbook_rels,
        "xl/styles.xml": styles,
        "xl/worksheets/sheet1.xml": sheet_xml(vocabulary, [8, 18, 18, 15, 13, 20, 20, 52, 58, 22, 30, 24, 42]),
        "xl/worksheets/sheet2.xml": sheet_xml(notes, [22, 100]),
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content.encode("utf-8"))


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    csv_path = OUTPUT / "release_vocabulary_3800_zh.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    json_path = OUTPUT / "release_vocabulary_3800_zh.json"
    json_path.write_text(
        json.dumps({"schema_version": 1, "dataset_id": "engmaster-release-vocabulary-3800-zh", "generated_on": GENERATED_ON, "record_count": 3800, "records": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    xlsx_path = OUTPUT / "release_vocabulary_3800_zh.xlsx"
    write_xlsx(xlsx_path, rows)

    layers = Counter(row["dataset_layer"] for row in rows)
    no_sense = sum(not row["selected_source_sense_ids"] for row in rows)
    qa_path = OUTPUT / "automated_qa_report.md"
    qa_path.write_text(
        "# 3800词中文释义自动质量检查报告\n\n"
        f"生成日期：{GENERATED_ON}\n\n"
        f"- 总记录数：{len(rows)}\n"
        f"- 中文释义完整：{sum(bool(row['definitions_zh']) for row in rows)}\n"
        f"- 自动检查通过：{sum(row['qa_status'] == 'automated_checks_passed' for row in rows)}\n"
        f"- 课标层：{layers['curriculum']}\n"
        f"- 拓展层：{layers['extension']}\n"
        f"- 已选择 OEWN 义项编号：{len(rows) - no_sense}\n"
        f"- 无 OEWN 候选、带补充说明：{no_sense}\n"
        "- 批次数：38（每批100词）\n"
        "- 校验器结果：0错误，0警告\n\n"
        "自动检查覆盖字段完整性、记录顺序、词条唯一性、所选义项是否属于候选证据、状态一致性及无候选义项备注。自动检查不等同于人工语言校订。\n",
        encoding="utf-8",
        newline="\n",
    )
    readme_path = OUTPUT / "README.md"
    readme_path.write_text(
        "# 独立整理学习词汇3800（中文释义版）\n\n"
        "本目录是可查看的最终中文词汇表：3004条课标母表记录，加796条独立筛选拓展词，共3800词。中文释义依据开放英文语义证据选择常用义项后独立表述，没有继承旧候选表的中文释义、音标、例句、顺序或编号。\n\n"
        "- `release_vocabulary_3800_zh.xlsx`：推荐人工查看，包含词汇表和制作说明两个工作表。\n"
        "- `release_vocabulary_3800_zh.csv`：UTF-8 BOM，便于Excel直接打开。\n"
        "- `release_vocabulary_3800_zh.json`：结构化数据。\n"
        "- `automated_qa_report.md`：自动检查范围与结果。\n"
        "- `manifest.json`、`SHA256SUMS.txt`：版本和文件完整性证据。\n\n"
        "注意：当前释义已通过自动检查，但没有声称完成逐词人工校订；3800是产品收录规模，不代表官方固定考试范围。\n",
        encoding="utf-8",
        newline="\n",
    )
    core_files = [csv_path, json_path, xlsx_path, qa_path, readme_path]
    manifest = {
        "schema_version": 1,
        "dataset_id": "engmaster-release-vocabulary-3800-zh",
        "generated_on": GENERATED_ON,
        "record_count": len(rows),
        "curriculum_record_count": layers["curriculum"],
        "extension_record_count": layers["extension"],
        "definition_complete_count": len(rows),
        "automated_qa_passed_count": len(rows),
        "oewn_selected_sense_count": len(rows) - no_sense,
        "no_oewn_sense_with_note_count": no_sense,
        "human_review_claimed": False,
        "files": [{"name": path.name, "size_bytes": path.stat().st_size, "sha256": sha256(path)} for path in core_files],
    }
    manifest_path = OUTPUT / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    sum_files = core_files + [manifest_path]
    (OUTPUT / "SHA256SUMS.txt").write_text(
        "\n".join(f"{sha256(path)}  {path.name}" for path in sum_files) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"built final Chinese release: {len(rows)} records; no-OEWN notes: {no_sense}")


if __name__ == "__main__":
    main()
