"""Build the traceable OEWN English-semantic base for the 3,800-word release."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data_sources/clean/release_word_master_3800/release_word_master_3800.csv"
DEFAULT_OEWN = ROOT / "data_sources/raw/oewn/english-wordnet-2025-json.zip"
DEFAULT_OUTPUT = ROOT / "data_sources/enrichment/oewn_semantic_base"

CSV_FIELDS = [
    "record_id",
    "word",
    "dataset_layer",
    "match_status",
    "matched_lemmas",
    "parts_of_speech",
    "sense_count",
    "lexicographer_classes",
    "english_definitions",
    "semantic_status",
]

POS_MAP = {
    "n": "noun",
    "v": "verb",
    "a": "adjective",
    "s": "adjective_satellite",
    "r": "adverb",
}


def read_master(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalized_pos(code: str) -> str:
    base = code.split("-", 1)[0]
    return POS_MAP.get(base, base)


def load_matching_entries(
    archive: zipfile.ZipFile, wanted_casefold: set[str]
) -> tuple[dict[str, dict[str, object]], dict[str, set[str]]]:
    exact: dict[str, dict[str, object]] = {}
    folded: dict[str, set[str]] = defaultdict(set)
    for name in sorted(archive.namelist()):
        if not Path(name).name.startswith("entries-") or not name.endswith(".json"):
            continue
        data = json.loads(archive.read(name))
        for lemma, by_pos in data.items():
            if lemma.casefold() not in wanted_casefold:
                continue
            senses: list[dict[str, str]] = []
            for pos_code, details in by_pos.items():
                for sense in details.get("sense", []):
                    synset = sense.get("synset")
                    if synset:
                        senses.append(
                            {
                                "source_pos_code": pos_code,
                                "part_of_speech": normalized_pos(pos_code),
                                "sense_id": sense.get("id", ""),
                                "synset_id": synset,
                            }
                        )
            exact[lemma] = {"lemma": lemma, "senses": senses}
            folded[lemma.casefold()].add(lemma)
    return exact, folded


def choose_lemmas(
    row: dict[str, str], exact: dict[str, dict[str, object]], folded: dict[str, set[str]]
) -> tuple[str, list[str]]:
    word = row["word"]
    variants = [item for item in row["variants"].split("|") if item]
    exact_headword = [word] if word in exact else []
    exact_variants = [variant for variant in variants if variant in exact]
    if exact_headword:
        return "exact_headword", exact_headword + exact_variants
    if exact_variants:
        return "exact_variant", exact_variants

    # Case folding is only safe for lowercase lexical items. It must not map
    # US -> us, China -> china, or other intentional curriculum case pairs.
    if word == word.lower():
        folded_headword = sorted(folded.get(word.casefold(), set()), key=str.casefold)
        if folded_headword:
            return "casefold_headword", folded_headword
        folded_variants = sorted(
            {lemma for variant in variants for lemma in folded.get(variant.casefold(), set())},
            key=str.casefold,
        )
        if folded_variants:
            return "casefold_variant", folded_variants
    return "no_oewn_match", []


def load_synsets(
    archive: zipfile.ZipFile, wanted_synsets: set[str]
) -> dict[str, dict[str, object]]:
    output: dict[str, dict[str, object]] = {}
    for name in archive.namelist():
        base = Path(name).name
        if base.startswith("entries-") or not base.endswith(".json"):
            continue
        lexclass = base[:-5]
        if not lexclass.startswith(("noun.", "verb.", "adj.", "adv.")):
            continue
        data = json.loads(archive.read(name))
        for synset_id in wanted_synsets & data.keys():
            synset = data[synset_id]
            output[synset_id] = {
                "lexicographer_class": lexclass,
                "definitions_en": synset.get("definition", []),
            }
    return output


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_report(path: Path, records: list[dict[str, object]]) -> None:
    matches = Counter(str(row["match_status"]) for row in records)
    layers = Counter(
        (str(row["dataset_layer"]), str(row["semantic_status"])) for row in records
    )
    pos_covered = sum(bool(row["parts_of_speech"]) for row in records)
    sense_covered = sum(int(row["sense_count"]) > 0 for row in records)
    lines = [
        "# 3800词 OEWN 英文语义底稿报告",
        "",
        "## 用途边界",
        "",
        "本底稿从 Open English WordNet 2025 提取词头、词性、synset、英文义项和 lexicographer class，用作后续中文释义的语义依据。它不是最终中文词库；没有使用旧中文释义，也没有生成音标。",
        "",
        f"- 发行记录：{len(records)}",
        f"- 获得词性证据：{pos_covered}",
        f"- 获得至少一个OEWN义项：{sense_covered}",
        f"- 待其他来源补充：{len(records) - sense_covered}",
        "",
        "## 匹配方式",
        "",
        "| 匹配状态 | 数量 |",
        "| --- | ---: |",
    ]
    for key in sorted(matches):
        lines.append(f"| {key} | {matches[key]} |")
    lines.extend(["", "## 分层覆盖", "", "| 数据层 | 状态 | 数量 |", "| --- | --- | ---: |"])
    for (layer, status), count in sorted(layers.items()):
        lines.append(f"| {layer} | {status} | {count} |")
    lines.extend(
        [
            "",
            "## 许可证",
            "",
            "Open English WordNet 2025 的OEWN部分使用 CC BY 4.0，并要求同时保留 Princeton WordNet 和 Open English WordNet Team 的署名。完整许可证见 `data_sources/raw/oewn/LICENSE.md` 及项目第三方声明。",
            "",
            "## 下一步",
            "",
            "无OEWN义项或大小写敏感未匹配项进入Moby/ECDICT词性补充清单；有多个义项的词在生成中文释义时按高中适用性筛选，不能把全部专业义项机械翻译。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--oewn", type=Path, default=DEFAULT_OEWN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    master = read_master(args.input)
    wanted = {
        form.casefold()
        for row in master
        for form in [row["word"], *filter(None, row["variants"].split("|"))]
    }
    with zipfile.ZipFile(args.oewn) as archive:
        exact, folded = load_matching_entries(archive, wanted)
        selections = [choose_lemmas(row, exact, folded) for row in master]
        synset_ids = {
            sense["synset_id"]
            for (_, lemmas) in selections
            for lemma in lemmas
            for sense in exact[lemma]["senses"]
        }
        synsets = load_synsets(archive, synset_ids)

    records: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for source, (match_status, lemmas) in zip(master, selections):
        senses: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()
        for lemma in lemmas:
            for sense_ref in exact[lemma]["senses"]:
                key = (lemma, sense_ref["sense_id"])
                if key in seen:
                    continue
                seen.add(key)
                synset = synsets.get(sense_ref["synset_id"], {})
                senses.append(
                    {
                        "matched_lemma": lemma,
                        **sense_ref,
                        "lexicographer_class": synset.get("lexicographer_class", ""),
                        "definitions_en": synset.get("definitions_en", []),
                    }
                )
        parts = sorted({str(sense["part_of_speech"]) for sense in senses})
        lexclasses = sorted(
            {str(sense["lexicographer_class"]) for sense in senses if sense["lexicographer_class"]}
        )
        definitions = []
        for sense in senses:
            definitions.extend(str(item) for item in sense["definitions_en"])
        semantic_status = "oewn_semantic_base_ready" if senses else "needs_non_oewn_review"
        record = {
            "record_id": source["record_id"],
            "word": source["word"],
            "variants": [item for item in source["variants"].split("|") if item],
            "dataset_layer": source["dataset_layer"],
            "match_status": match_status,
            "matched_lemmas": lemmas,
            "parts_of_speech": parts,
            "sense_count": len(senses),
            "lexicographer_classes": lexclasses,
            "senses": senses,
            "semantic_status": semantic_status,
            "semantic_source": "Open English WordNet 2025",
            "license": "Princeton WordNet License + CC BY 4.0",
        }
        records.append(record)
        summary_rows.append(
            {
                "record_id": source["record_id"],
                "word": source["word"],
                "dataset_layer": source["dataset_layer"],
                "match_status": match_status,
                "matched_lemmas": "|".join(lemmas),
                "parts_of_speech": "|".join(parts),
                "sense_count": len(senses),
                "lexicographer_classes": "|".join(lexclasses),
                "english_definitions": " || ".join(definitions),
                "semantic_status": semantic_status,
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "oewn_semantic_base.json"
    json_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dataset_id": "engmaster-oewn-semantic-base-3800",
                "record_count": len(records),
                "source": "Open English WordNet 2025",
                "license": "Princeton WordNet License + CC BY 4.0",
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    csv_path = args.output_dir / "oewn_semantic_base_summary.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(summary_rows)
    missing_path = args.output_dir / "needs_non_oewn_review.csv"
    with missing_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(
            row for row in summary_rows if row["semantic_status"] == "needs_non_oewn_review"
        )
    report_path = args.output_dir / "README.md"
    write_report(report_path, records)
    written = [json_path, csv_path, missing_path, report_path]
    checksum_path = args.output_dir / "SHA256SUMS.txt"
    checksum_path.write_text(
        "\n".join(f"{sha256(path)}  {path.name}" for path in sorted(written)) + "\n",
        encoding="ascii",
    )
    print(f"Built OEWN semantic base for {len(records)} records")
    print(Counter(record["semantic_status"] for record in records))
    print(Counter(record["match_status"] for record in records))


if __name__ == "__main__":
    main()
