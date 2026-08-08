"""Rebuild the irregular-verb table from factual forms and open evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_PATH = ROOT / "assets/irregular_verbs.json"
BATCH_DIR = ROOT / "data_sources/enrichment/chinese_definition_batches"
WNDB_PATH = ROOT / "data_sources/raw/oewn/english-wordnet-2025-wndb.zip"
OUTPUT = ROOT / "data_sources/clean/irregular_verbs"
GENERATED_ON = "2026-08-08"

# Every lemma is stated explicitly. The old table supplies only the candidate
# lemma index; none of its forms, Chinese meanings, IDs, or formatting are read
# into the release records.
CURATED_FORMS: dict[str, tuple[list[str], list[str]]] = {
    "arise": (["arose"], ["arisen"]),
    "be": (["was", "were"], ["been"]),
    "beat": (["beat"], ["beaten"]),
    "become": (["became"], ["become"]),
    "begin": (["began"], ["begun"]),
    "bend": (["bent"], ["bent"]),
    "bet": (["bet", "betted"], ["bet", "betted"]),
    "bite": (["bit"], ["bitten"]),
    "bleed": (["bled"], ["bled"]),
    "blow": (["blew"], ["blown"]),
    "break": (["broke"], ["broken"]),
    "bring": (["brought"], ["brought"]),
    "broadcast": (["broadcast"], ["broadcast"]),
    "build": (["built"], ["built"]),
    "burn": (["burned", "burnt"], ["burned", "burnt"]),
    "burst": (["burst"], ["burst"]),
    "buy": (["bought"], ["bought"]),
    "can": (["could"], []),
    "catch": (["caught"], ["caught"]),
    "choose": (["chose"], ["chosen"]),
    "come": (["came"], ["come"]),
    "cost": (["cost"], ["cost"]),
    "cut": (["cut"], ["cut"]),
    "deal": (["dealt"], ["dealt"]),
    "dig": (["dug"], ["dug"]),
    "do": (["did"], ["done"]),
    "draw": (["drew"], ["drawn"]),
    "dream": (["dreamed", "dreamt"], ["dreamed", "dreamt"]),
    "drink": (["drank"], ["drunk"]),
    "drive": (["drove"], ["driven"]),
    "eat": (["ate"], ["eaten"]),
    "fall": (["fell"], ["fallen"]),
    "feed": (["fed"], ["fed"]),
    "feel": (["felt"], ["felt"]),
    "fight": (["fought"], ["fought"]),
    "find": (["found"], ["found"]),
    "fly": (["flew"], ["flown"]),
    "foresee": (["foresaw"], ["foreseen"]),
    "forget": (["forgot"], ["forgotten"]),
    "forgive": (["forgave"], ["forgiven"]),
    "freeze": (["froze"], ["frozen"]),
    "get": (["got"], ["got", "gotten"]),
    "give": (["gave"], ["given"]),
    "go": (["went"], ["gone"]),
    "grow": (["grew"], ["grown"]),
    "hang": (["hung", "hanged"], ["hung", "hanged"]),
    "have": (["had"], ["had"]),
    "hear": (["heard"], ["heard"]),
    "hide": (["hid"], ["hidden"]),
    "hit": (["hit"], ["hit"]),
    "hold": (["held"], ["held"]),
    "hurt": (["hurt"], ["hurt"]),
    "keep": (["kept"], ["kept"]),
    "know": (["knew"], ["known"]),
    "lay": (["laid"], ["laid"]),
    "lead": (["led"], ["led"]),
    "learn": (["learned", "learnt"], ["learned", "learnt"]),
    "leave": (["left"], ["left"]),
    "lend": (["lent"], ["lent"]),
    "let": (["let"], ["let"]),
    "lie": (["lay"], ["lain"]),
    "light": (["lit", "lighted"], ["lit", "lighted"]),
    "lose": (["lost"], ["lost"]),
    "make": (["made"], ["made"]),
    "may": (["might"], []),
    "mean": (["meant"], ["meant"]),
    "meet": (["met"], ["met"]),
    "misread": (["misread"], ["misread"]),
    "mistake": (["mistook"], ["mistaken"]),
    "misunderstand": (["misunderstood"], ["misunderstood"]),
    "must": ([], []),
    "pay": (["paid"], ["paid"]),
    "put": (["put"], ["put"]),
    "read": (["read"], ["read"]),
    "rid": (["rid", "ridded"], ["rid", "ridded"]),
    "ride": (["rode"], ["ridden"]),
    "ring": (["rang"], ["rung"]),
    "rise": (["rose"], ["risen"]),
    "run": (["ran"], ["run"]),
    "say": (["said"], ["said"]),
    "see": (["saw"], ["seen"]),
    "seek": (["sought"], ["sought"]),
    "sell": (["sold"], ["sold"]),
    "send": (["sent"], ["sent"]),
    "set": (["set"], ["set"]),
    "shake": (["shook"], ["shaken"]),
    "shall": (["should"], []),
    "shine": (["shone", "shined"], ["shone", "shined"]),
    "show": (["showed"], ["shown", "showed"]),
    "shut": (["shut"], ["shut"]),
    "sing": (["sang"], ["sung"]),
    "sink": (["sank", "sunk"], ["sunk"]),
    "sit": (["sat"], ["sat"]),
    "sleep": (["slept"], ["slept"]),
    "smell": (["smelled", "smelt"], ["smelled", "smelt"]),
    "sow": (["sowed"], ["sown", "sowed"]),
    "speak": (["spoke"], ["spoken"]),
    "spell": (["spelled", "spelt"], ["spelled", "spelt"]),
    "spellbind": (["spellbound"], ["spellbound"]),
    "spend": (["spent"], ["spent"]),
    "spill": (["spilled", "spilt"], ["spilled", "spilt"]),
    "spin": (["spun"], ["spun"]),
    "spit": (["spat", "spit"], ["spat", "spit"]),
    "spoil": (["spoiled", "spoilt"], ["spoiled", "spoilt"]),
    "spread": (["spread"], ["spread"]),
    "stand": (["stood"], ["stood"]),
    "steal": (["stole"], ["stolen"]),
    "stick": (["stuck"], ["stuck"]),
    "strike": (["struck"], ["struck", "stricken"]),
    "swell": (["swelled"], ["swollen", "swelled"]),
    "sweep": (["swept"], ["swept"]),
    "swim": (["swam"], ["swum"]),
    "swing": (["swung"], ["swung"]),
    "take": (["took"], ["taken"]),
    "teach": (["taught"], ["taught"]),
    "tell": (["told"], ["told"]),
    "think": (["thought"], ["thought"]),
    "throw": (["threw"], ["thrown"]),
    "understand": (["understood"], ["understood"]),
    "upset": (["upset"], ["upset"]),
    "wake": (["woke", "waked"], ["woken", "waked"]),
    "wear": (["wore"], ["worn"]),
    "weave": (["wove", "weaved"], ["woven", "weaved"]),
    "will": (["would"], []),
    "win": (["won"], ["won"]),
    "write": (["wrote"], ["written"]),
}

REGULAR_VARIANTS = {
    "bet": {"betted"},
    "burn": {"burned"},
    "dream": {"dreamed"},
    "hang": {"hanged"},
    "learn": {"learned"},
    "light": {"lighted"},
    "rid": {"ridded"},
    "shine": {"shined"},
    "show": {"showed"},
    "smell": {"smelled"},
    "sow": {"sowed"},
    "spell": {"spelled"},
    "spill": {"spilled"},
    "spoil": {"spoiled"},
    "swell": {"swelled"},
    "wake": {"waked"},
    "weave": {"weaved"},
}

HISTORICAL_MODAL_FORMS = {
    "can": {"could"},
    "may": {"might"},
    "shall": {"should"},
    "will": {"would"},
}

DOCUMENTED_LEXICAL_VARIANTS = {
    "strike": {"stricken"},
}

SUPPLEMENTAL_MEANINGS = {
    "misread": "误读；看错",
    "spellbind": "迷住；使入迷",
    "spill": "溢出；洒出",
    "spoil": "破坏；宠坏",
    "weave": "编织；穿梭",
}

USAGE_NOTES = {
    "be": "过去式按人称和单复数使用 was 或 were。",
    "can": "could 是历史上的过去式，也常表达较弱语气；没有过去分词。",
    "get": "got 为常见过去分词；gotten 主要见于美式英语及部分固定意义。",
    "hang": "表示悬挂通常用 hung；表示绞死通常用 hanged。",
    "lie": "本行表示“躺；位于”；表示“说谎”时规则变化为 lied。",
    "may": "might 是历史上的过去式，也常表达较弱可能性；没有过去分词。",
    "must": "现代英语中没有独立过去式或过去分词；过去时意义通常用 had to。",
    "read": "过去式和过去分词拼写仍为 read，但读音与原形不同。",
    "shall": "should 是历史上的过去式，也可表达建议或义务；没有过去分词。",
    "shine": "shone 常指发光；shined 常用于擦亮或使发亮。",
    "spit": "spat 较常见；spit 也可作过去式和过去分词，尤其见于美式英语。",
    "strike": "struck 是一般过去分词；stricken 常用于受疾病、灾难或情感打击。",
    "weave": "wove/woven 常指编织；weaved 常用于迂回穿行。",
    "will": "would 是历史上的过去式，也用于条件、意愿等结构；没有过去分词。",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_exception_map() -> dict[str, set[str]]:
    with zipfile.ZipFile(WNDB_PATH) as archive:
        lines = archive.read("oewn2025/verb.exc").decode("utf-8").splitlines()
    mapping: dict[str, set[str]] = {}
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            mapping.setdefault(parts[0], set()).update(parts[1:])
    return mapping


def load_meanings() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for path in sorted(BATCH_DIR.glob("batch_[0-9][0-9][0-9].json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for record in payload["records"]:
            verb_defs = [
                item["definition"] for item in record["definitions_zh"]
                if "verb" in item["part_of_speech"]
            ]
            if verb_defs:
                result[record["word"]] = {
                    "meaning": "；".join(verb_defs),
                    "record_id": record["record_id"],
                }
    return result


def evidence_for(lemma: str, form: str, exceptions: dict[str, set[str]]) -> str:
    if form == lemma:
        return "same_spelling_irregular_form"
    if lemma in exceptions.get(form, set()):
        return "oewn_verb_exception"
    if form in REGULAR_VARIANTS.get(lemma, set()):
        return "productive_regular_variant"
    if form in HISTORICAL_MODAL_FORMS.get(lemma, set()):
        return "historical_modal_form"
    if form in DOCUMENTED_LEXICAL_VARIANTS.get(lemma, set()):
        return "documented_lexical_variant"
    raise ValueError(f"Unsupported form: {lemma} -> {form}")


def col_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def sheet_xml(values: list[list[str]], widths: list[int]) -> str:
    rows = []
    for row_number, row in enumerate(values, 1):
        cells = []
        for column, value in enumerate(row, 1):
            ref = f"{col_name(column)}{row_number}"
            style = 1 if row_number == 1 else 2
            safe = escape(str(value), {'"': "&quot;"})
            cells.append(f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{safe}</t></is></c>')
        rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')
    columns = "".join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths, 1))
    last = f"{col_name(len(values[0]))}{len(values)}"
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<dimension ref="A1:{last}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" state="frozen"/></sheetView></sheetViews>'
            f'<cols>{columns}</cols><sheetData>{"".join(rows)}</sheetData><autoFilter ref="A1:{last}"/></worksheet>')


def write_xlsx(path: Path, rows: list[dict[str, str]]) -> None:
    headers = ["序号", "原形", "过去式", "过去分词", "中文释义", "3800词表记录", "使用说明", "校验状态"]
    fields = ["sequence", "infinitive", "past_tense", "past_participle", "meaning_zh", "release_record_id", "usage_note", "qa_status"]
    table = [headers] + [[row[field] for field in fields] for row in rows]
    notes = [
        ["项目", "说明"],
        ["候选范围", "沿用旧表126个原形作为待核对索引；旧表词形和释义不进入新表。"],
        ["词形依据", "Open English WordNet 2025 verb.exc；规则变体及同形变化另行标注。"],
        ["中文释义", "取自独立制作的3800词中文释义；未覆盖5词采用本项目独立补充释义。"],
        ["审核状态", "已通过自动完整性与来源对应检查；未声称人工专家校订。"],
    ]
    workbook = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="不规则动词表" sheetId="1" r:id="rId1"/><sheet name="制作说明" sheetId="2" r:id="rId2"/></sheets></workbook>'
    styles = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="10"/><name val="Microsoft YaHei"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Microsoft YaHei"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF305496"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellXfs count="3"><xf/><xf fontId="1" fillId="2" applyFont="1" applyFill="1"/><xf><alignment vertical="top" wrapText="1"/></xf></cellXfs></styleSheet>'
    types = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>'
    root_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    book_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'
    parts = {"[Content_Types].xml": types, "_rels/.rels": root_rels, "xl/workbook.xml": workbook,
             "xl/_rels/workbook.xml.rels": book_rels, "xl/styles.xml": styles,
             "xl/worksheets/sheet1.xml": sheet_xml(table, [8, 16, 24, 24, 35, 22, 58, 22]),
             "xl/worksheets/sheet2.xml": sheet_xml(notes, [22, 100])}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content.encode("utf-8"))


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    old_rows = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8-sig"))
    candidates = [str(row["infinitive"]).strip().lower() for row in old_rows]
    if len(candidates) != 126 or len(set(candidates)) != 126:
        raise ValueError("Expected 126 unique legacy candidate lemmas")
    if set(candidates) != set(CURATED_FORMS):
        raise ValueError("Curated lemma set differs from candidate index")

    meanings = load_meanings()
    exceptions = load_exception_map()
    records = []
    evidence_rows = []
    for sequence, lemma in enumerate(candidates, 1):
        past, participle = CURATED_FORMS[lemma]
        meaning_info = meanings.get(lemma)
        if meaning_info:
            meaning = meaning_info["meaning"]
            release_id = meaning_info["record_id"]
            meaning_source = "release_vocabulary_3800_zh"
        else:
            meaning = SUPPLEMENTAL_MEANINGS.get(lemma, "")
            release_id = ""
            meaning_source = "independent_project_supplement"
        if not meaning or not re.search(r"[\u3400-\u9fff]", meaning):
            raise ValueError(f"Missing Chinese verb meaning: {lemma}")

        for slot, forms in (("past_tense", past), ("past_participle", participle)):
            if not forms:
                evidence_rows.append({"infinitive": lemma, "slot": slot, "form": "",
                                      "evidence_type": "not_applicable_modal", "source": "project_usage_analysis"})
            for form in forms:
                kind = evidence_for(lemma, form, exceptions)
                source = "Open English WordNet 2025 verb.exc" if kind == "oewn_verb_exception" else "project_rule_documentation"
                evidence_rows.append({"infinitive": lemma, "slot": slot, "form": form,
                                      "evidence_type": kind, "source": source})
        records.append({
            "sequence": sequence,
            "infinitive": lemma,
            "accepted_past_tense": past,
            "accepted_past_participle": participle,
            "past_tense": " / ".join(past) if past else "—",
            "past_participle": " / ".join(participle) if participle else "—",
            "meaning_zh": meaning,
            "in_release_3800": bool(release_id),
            "release_record_id": release_id,
            "usage_note": USAGE_NOTES.get(lemma, ""),
            "form_source": "OEWN 2025 verb.exc + documented form rules",
            "meaning_source": meaning_source,
            "qa_status": "automated_checks_passed",
        })

    json_payload = {
        "schema_version": 1,
        "dataset": "EngMaster independently rebuilt irregular verb table",
        "generated_on": GENERATED_ON,
        "record_count": len(records),
        "candidate_index_only": "assets/irregular_verbs.json",
        "human_review_claimed": False,
        "records": records,
    }
    json_path = OUTPUT / "irregular_verbs_clean.json"
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    display_fields = ["sequence", "infinitive", "past_tense", "past_participle", "meaning_zh",
                      "in_release_3800", "release_record_id", "usage_note", "form_source", "meaning_source", "qa_status"]
    display_rows = [{field: str(row[field]) for field in display_fields} for row in records]
    csv_path = OUTPUT / "irregular_verbs_clean.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=display_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(display_rows)

    evidence_path = OUTPUT / "irregular_form_evidence.csv"
    with evidence_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["infinitive", "slot", "form", "evidence_type", "source"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(evidence_rows)
    write_xlsx(OUTPUT / "irregular_verbs_clean.xlsx", display_rows)

    legacy_rows = [{"infinitive": row["infinitive"], "past_tense": row["past_tense"],
                    "past_participle": row["past_participle"], "meaning": row["meaning_zh"]} for row in records]
    legacy_path = OUTPUT / "irregular_verbs_legacy_compatible.json"
    legacy_path.write_text(json.dumps(legacy_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    changed = []
    for old, new in zip(old_rows, records):
        differences = []
        if old.get("past_tense", "") != new["past_tense"]:
            differences.append(f"过去式：`{old.get('past_tense', '')}` → `{new['past_tense']}`")
        if old.get("past_participle", "") != new["past_participle"]:
            differences.append(f"过去分词：`{old.get('past_participle', '')}` → `{new['past_participle']}`")
        if differences:
            changed.append(f"- **{new['infinitive']}**：" + "；".join(differences))
    audit = f"""# 不规则动词表清洗审计报告

- 生成日期：{GENERATED_ON}
- 旧表候选词头：126（仅作待核对索引）
- 新表记录：{len(records)}
- 进入3800独立词表：{sum(r['in_release_3800'] for r in records)}
- 项目独立补充释义：{sum(not r['in_release_3800'] for r in records)}
- 自动校验错误：0
- 人工专家审核声明：无

## 来源边界

旧文件 `assets/irregular_verbs.json` 只用于确定需要核对的126个原形。新表没有读取或继承旧表的过去式、过去分词和中文释义。词形证据来自 Open English WordNet 2025 的 `verb.exc`，同形不规则变化和规则并存变体按明确规则记录；中文释义优先来自本项目独立制作的3800词表。

## 与旧表的词形展示差异

{chr(10).join(changed) if changed else '- 无'}

这些差异不表示旧表全部错误，主要是补充可接受变体、统一斜线两侧空格，以及把没有过去分词的情态动词明确标成“—”。
"""
    (OUTPUT / "audit_report.md").write_text(audit, encoding="utf-8", newline="\n")
    readme = """# 独立重建不规则动词表

本目录是可追溯的清洗产物。旧表仅作为候选词头索引；新词形和中文释义均从已记录的独立来源重新建立。

主要文件：

- `irregular_verbs_clean.xlsx`：便于查看的正式表格。
- `irregular_verbs_clean.json/csv`：结构化正式数据。
- `irregular_verbs_legacy_compatible.json`：供现有程序替换数据时使用，尚未自动覆盖产品文件。
- `irregular_form_evidence.csv`：每个过去式、过去分词的证据分类。
- `audit_report.md`：数量、来源边界及与旧表的差异。
- `manifest.json`、`SHA256SUMS.txt`：构建说明与文件校验值。

许可提示：OEWN 2025 采用 CC BY 4.0，并包含 Princeton WordNet 的归属要求。发布产品时须随附项目已有的第三方许可声明。
"""
    (OUTPUT / "README.md").write_text(readme, encoding="utf-8", newline="\n")

    artifact_names = ["irregular_verbs_clean.json", "irregular_verbs_clean.csv", "irregular_verbs_clean.xlsx",
                      "irregular_verbs_legacy_compatible.json", "irregular_form_evidence.csv", "audit_report.md", "README.md"]
    manifest = {
        "schema_version": 1, "generated_on": GENERATED_ON, "record_count": len(records),
        "legacy_candidate_count": len(candidates), "release_3800_matches": sum(r["in_release_3800"] for r in records),
        "supplemental_meanings": sorted(SUPPLEMENTAL_MEANINGS), "human_review_claimed": False,
        "source_archive": str(WNDB_PATH.relative_to(ROOT)).replace("\\", "/"),
        "source_archive_sha256": sha256(WNDB_PATH), "artifacts": artifact_names,
    }
    manifest_path = OUTPUT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    checksum_names = artifact_names + ["manifest.json"]
    checksum_text = "".join(f"{sha256(OUTPUT / name)}  {name}\n" for name in checksum_names)
    (OUTPUT / "SHA256SUMS.txt").write_text(checksum_text, encoding="utf-8", newline="\n")
    print(f"Built {len(records)} records; {len(evidence_rows)} evidence rows; {len(changed)} display differences.")


if __name__ == "__main__":
    main()
