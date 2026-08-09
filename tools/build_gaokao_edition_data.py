"""Build the isolated, copyright-audited data package for the gaokao edition."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "assets/editions/gaokao"
VOCABULARY_SOURCE = (
    ROOT
    / "data_sources/clean/release_vocabulary_3800_zh/release_vocabulary_3800_zh.json"
)
IPA_SOURCE = (
    ROOT
    / "data_sources/clean/release_vocabulary_3800_ipa/release_vocabulary_3800_ipa.json"
)
PHRASE_SOURCE = (
    ROOT
    / "data_sources/clean/phrase_product_candidates/senior_high_phrases_product_candidate.json"
)
IRREGULAR_SOURCE = (
    ROOT / "data_sources/clean/irregular_verbs/irregular_verbs_clean.json"
)
NOTICE_SOURCE = ROOT / "data_sources/provenance_evidence/THIRD_PARTY_NOTICES.md"
OEWN_LICENSE_SOURCE = ROOT / "data_sources/raw/oewn/LICENSE.md"
ECDICT_LICENSE_SOURCE = ROOT / "data_sources/raw/ecdict/LICENSE"
IPA_DICT_LICENSE_SOURCE = ROOT / "data_sources/raw/ipa_dict/LICENSE"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    rows = payload.get("records")
    if not isinstance(rows, list):
        raise ValueError(f"Expected a list or records list in {path}")
    return rows


def build_vocabulary() -> list[dict[str, object]]:
    rows = load_rows(VOCABULARY_SOURCE)
    ipa_by_id = {
        str(row["record_id"]): row for row in load_rows(IPA_SOURCE)
    }
    output: list[dict[str, object]] = []
    for row in rows:
        variants = [
            value.strip()
            for value in str(row["variants"] or "").split(";")
            if value.strip()
        ]
        item = {
            "word": row["word"],
            "content": row["definitions_zh"],
            "record_id": row["record_id"],
            "variants": row["variants"],
            "dataset_layer": row["dataset_layer"],
            "curriculum_level": row["curriculum_level"],
            "parts_of_speech": row["parts_of_speech"],
            "definition_method": row["definition_method"],
            "qa_status": row["qa_status"],
            "pronunciation": ipa_by_id[str(row["record_id"])]["pronunciation"],
            "pronunciation_source": "ipa-dict en_US",
            "pronunciation_match_method": ipa_by_id[
                str(row["record_id"])
            ]["match_method"],
        }
        if variants:
            item["accepted_answers"] = variants
        output.append(item)
    return output


def build_irregulars() -> list[dict[str, object]]:
    rows = load_rows(IRREGULAR_SOURCE)
    return [
        {
            "infinitive": row["infinitive"],
            "past_tense": row["past_tense"],
            "past_participle": row["past_participle"],
            "meaning": row["meaning_zh"],
            "accepted_past_tense": row["accepted_past_tense"],
            "accepted_past_participle": row["accepted_past_participle"],
            "release_record_id": row["release_record_id"],
            "form_source": row["form_source"],
            "meaning_source": row["meaning_source"],
            "qa_status": row["qa_status"],
        }
        for row in rows
    ]


def build_phrases() -> list[dict[str, object]]:
    rows = load_rows(PHRASE_SOURCE)
    output: list[dict[str, object]] = []
    for index, original in enumerate(rows):
        row = dict(original)
        if index < 300:
            row["tier"] = "core"
            row["level"] = index // 50 + 1
        else:
            row["tier"] = "extension"
            row["level"] = (index - 300) // 50 + 1
        output.append(row)
    return output


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_readme() -> Path:
    path = OUTPUT_DIR / "README.md"
    path.write_text(
        """# 高中英语完整数据包

本目录是高中正式版在程序内实际读取的独立数据区：

- `vocabulary.json`：3800条高中学习词汇、中文释义及美式IPA音标；
- `trial_vocabulary.json`：从正式词表原样提取的30条高中体验词；
- `phrases.json`：450条高中短语，其中核心300条（6关）、扩展150条（3关）；
- `irregular_verbs.json`：126条不规则动词；
- `manifest.json`、`SHA256SUMS.txt`：来源和成品完整性记录；
- `THIRD_PARTY_NOTICES.md`、`OPEN_ENGLISH_WORDNET_LICENSE.md`、`PRINCETON_WORDNET_LICENSE.txt`、`ECDICT_LICENSE.txt`、`IPA_DICT_LICENSE.txt`：第三方来源与许可证声明。

本数据包不含图片和音频。美式IPA、中文释义、短语内容和不规则动词形式均来自仓库内已留档的干净母数据；不声明已经人工逐条审核。
""",
        encoding="utf-8",
    )
    return path


def copy_text_normalized(source: Path, destination: Path) -> None:
    lines = source.read_text(encoding="utf-8").splitlines()
    destination.write_text(
        "\n".join(line.rstrip() for line in lines).rstrip() + "\n",
        encoding="utf-8",
    )


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    vocabulary = build_vocabulary()
    phrases = build_phrases()
    irregulars = build_irregulars()
    write_json(OUTPUT_DIR / "vocabulary.json", vocabulary)
    trial_ids = {
        str(row["record_id"])
        for row in load_rows(OUTPUT_DIR / "trial_vocabulary.json")
    }
    write_json(
        OUTPUT_DIR / "trial_vocabulary.json",
        [row for row in vocabulary if str(row["record_id"]) in trial_ids],
    )
    write_json(OUTPUT_DIR / "phrases.json", phrases)
    write_json(OUTPUT_DIR / "irregular_verbs.json", irregulars)
    shutil.copyfile(NOTICE_SOURCE, OUTPUT_DIR / "THIRD_PARTY_NOTICES.md")
    copy_text_normalized(
        OEWN_LICENSE_SOURCE,
        OUTPUT_DIR / "OPEN_ENGLISH_WORDNET_LICENSE.md",
    )
    copy_text_normalized(
        ECDICT_LICENSE_SOURCE,
        OUTPUT_DIR / "ECDICT_LICENSE.txt",
    )
    copy_text_normalized(
        IPA_DICT_LICENSE_SOURCE,
        OUTPUT_DIR / "IPA_DICT_LICENSE.txt",
    )
    readme_path = write_readme()

    data_files = [
        OUTPUT_DIR / "vocabulary.json",
        OUTPUT_DIR / "trial_vocabulary.json",
        OUTPUT_DIR / "phrases.json",
        OUTPUT_DIR / "irregular_verbs.json",
        OUTPUT_DIR / "THIRD_PARTY_NOTICES.md",
        OUTPUT_DIR / "OPEN_ENGLISH_WORDNET_LICENSE.md",
        OUTPUT_DIR / "PRINCETON_WORDNET_LICENSE.txt",
        OUTPUT_DIR / "ECDICT_LICENSE.txt",
        OUTPUT_DIR / "IPA_DICT_LICENSE.txt",
        readme_path,
    ]
    source_files = [
        VOCABULARY_SOURCE, IPA_SOURCE, PHRASE_SOURCE, IRREGULAR_SOURCE
    ]
    manifest = {
        "schema_version": 1,
        "edition_id": "gaokao",
        "status": "product_data_complete_auto_validated",
        "counts": {
            "vocabulary": len(vocabulary),
            "trial_vocabulary": 30,
            "phrases": len(phrases),
            "core_phrases": sum(row["tier"] == "core" for row in phrases),
            "extension_phrases": sum(
                row["tier"] == "extension" for row in phrases
            ),
            "irregular_verbs": len(irregulars),
        },
        "application_paths": {
            "vocabulary": "assets/editions/gaokao/vocabulary.json",
            "trial_vocabulary": "assets/editions/gaokao/trial_vocabulary.json",
            "phrases": "assets/editions/gaokao/phrases.json",
            "irregular_verbs": "assets/editions/gaokao/irregular_verbs.json",
        },
        "source_files": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path)
            for path in source_files
        },
        "product_files": {
            path.name: sha256_file(path) for path in data_files
        },
        "content_policy": {
            "legacy_vocabulary_content_reused": False,
            "legacy_phrase_content_reused": False,
            "legacy_irregular_index_used": True,
            "images_included": False,
            "audio_included": False,
            "phonetics_included": True,
            "phonetics_dialect": "General American",
            "phonetics_source": "ipa-dict en_US",
            "human_review_claimed": False,
        },
    }
    manifest_path = OUTPUT_DIR / "manifest.json"
    write_json(manifest_path, manifest)

    checksums = {
        **manifest["product_files"],
        "manifest.json": sha256_file(manifest_path),
    }
    (OUTPUT_DIR / "SHA256SUMS.txt").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(checksums.items())),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
