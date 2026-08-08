"""Generate a checksum manifest for the vocabulary provenance evidence chain."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data_sources/provenance_evidence"

EVIDENCE_FILES: dict[str, list[str]] = {
    "governance": [
        ".gitattributes",
        "词库命名与开放数据来源策略.md",
        "data_sources/provenance_evidence/词库来源与制作过程证明材料.md",
        "data_sources/provenance_evidence/THIRD_PARTY_NOTICES.md",
    ],
    "moe_source": [
        "data_sources/raw/moe/普通高中英语课程标准_2017年版2020年修订.pdf",
        "data_sources/raw/moe/source.json",
        "data_sources/raw/moe/download_records.md",
        "data_sources/raw/moe/SHA256SUMS.txt",
    ],
    "open_english_wordnet": [
        "data_sources/raw/oewn/english-wordnet-2025-json.zip",
        "data_sources/raw/oewn/LICENSE.md",
        "data_sources/raw/oewn/source.json",
        "data_sources/raw/oewn/SHA256SUMS.txt",
    ],
    "moby": [
        "data_sources/raw/moby/common.txt",
        "data_sources/raw/moby/mobypos.txt",
        "data_sources/raw/moby/moby_words_documentation.html",
        "data_sources/raw/moby/moby_pos_documentation.html",
        "data_sources/raw/moby/source.json",
        "data_sources/raw/moby/SHA256SUMS.txt",
    ],
    "ecdict": [
        "data_sources/raw/ecdict/ecdict.csv",
        "data_sources/raw/ecdict/LICENSE",
        "data_sources/raw/ecdict/README.md",
        "data_sources/raw/ecdict/source.json",
        "data_sources/raw/ecdict/SHA256SUMS.txt",
    ],
    "build_scripts": [
        "tools/extract_moe_curriculum_vocab.py",
        "tools/match_existing_vocab_to_curriculum.py",
        "tools/build_clean_curriculum_base.py",
        "tools/screen_extension_candidates.py",
        "tools/score_extension_relevance.py",
        "tools/resolve_extension_forms_and_reasons.py",
        "tools/review_hold_candidates.py",
        "tools/build_extension_priority_draft.py",
        "tools/build_extension_secondary_review_queue.py",
        "tools/finalize_word_master.py",
        "tools/build_release_word_master_3800.py",
        "tools/build_oewn_semantic_base.py",
        "tools/supplement_non_oewn_pos.py",
        "tools/prepare_chinese_definition_batches.py",
        "tools/apply_chinese_definition_draft.py",
        "tools/validate_chinese_definition_batches.py",
        "tools/export_chinese_definition_preview.py",
        "tools/build_release_vocabulary_3800_zh.py",
        "tools/build_vocabulary_provenance_evidence.py",
    ],
    "audit_reports": [
        "data_sources/processed/curriculum_vocabulary_report.md",
        "data_sources/processed/current_vocab_curriculum_match_report.md",
        "data_sources/processed/extension_screening_report.md",
        "data_sources/processed/extension_relevance_scoring_report.md",
        "data_sources/processed/extension_form_and_reason_report.md",
        "data_sources/processed/extension_hold_review_report.md",
    ],
    "clean_curriculum": [
        "data_sources/clean/curriculum_base.csv",
        "data_sources/clean/curriculum_base.json",
        "data_sources/clean/curriculum_base_manifest.json",
        "data_sources/clean/README.md",
        "data_sources/clean/SHA256SUMS.txt",
    ],
    "release_3800": [
        "data_sources/clean/release_word_master_3800/release_word_master_3800.csv",
        "data_sources/clean/release_word_master_3800/release_word_master_3800.json",
        "data_sources/clean/release_word_master_3800/manifest.json",
        "data_sources/clean/release_word_master_3800/README.md",
        "data_sources/clean/release_word_master_3800/SHA256SUMS.txt",
        "data_sources/clean/release_word_master_3800/legacy_overlap_and_size_report.md",
        "data_sources/clean/release_word_master_3800/legacy_word_overlap_mapping.csv",
        "data_sources/clean/release_word_master_3800/extensions_removed_for_3800_target.csv",
    ],
    "semantic_enrichment": [
        "data_sources/enrichment/oewn_semantic_base/oewn_semantic_base.json",
        "data_sources/enrichment/oewn_semantic_base/oewn_semantic_base_summary.csv",
        "data_sources/enrichment/oewn_semantic_base/needs_non_oewn_review.csv",
        "data_sources/enrichment/oewn_semantic_base/README.md",
        "data_sources/enrichment/oewn_semantic_base/SHA256SUMS.txt",
        "data_sources/enrichment/non_oewn_pos_supplement/release_3800_pos_evidence.csv",
        "data_sources/enrichment/non_oewn_pos_supplement/non_oewn_pos_supplement.csv",
        "data_sources/enrichment/non_oewn_pos_supplement/README.md",
        "data_sources/enrichment/non_oewn_pos_supplement/SHA256SUMS.txt",
        "data_sources/enrichment/chinese_definition_batches/batch_manifest.json",
        "data_sources/enrichment/chinese_definition_batches/README.md",
        "data_sources/enrichment/chinese_definition_batches/SHA256SUMS.txt",
    ],
    "chinese_release_3800": [
        "data_sources/clean/release_vocabulary_3800_zh/release_vocabulary_3800_zh.csv",
        "data_sources/clean/release_vocabulary_3800_zh/release_vocabulary_3800_zh.json",
        "data_sources/clean/release_vocabulary_3800_zh/release_vocabulary_3800_zh.xlsx",
        "data_sources/clean/release_vocabulary_3800_zh/automated_qa_report.md",
        "data_sources/clean/release_vocabulary_3800_zh/manifest.json",
        "data_sources/clean/release_vocabulary_3800_zh/README.md",
        "data_sources/clean/release_vocabulary_3800_zh/SHA256SUMS.txt",
    ],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> None:
    EVIDENCE_FILES["chinese_definition_batches"] = [
        str(path.relative_to(ROOT)).replace("\\", "/")
        for path in sorted((ROOT / "data_sources/enrichment/chinese_definition_batches").glob("batch_[0-9][0-9][0-9].json"))
    ]
    EVIDENCE_FILES["chinese_definition_drafts"] = [
        str(path.relative_to(ROOT)).replace("\\", "/")
        for path in sorted((ROOT / "data_sources/enrichment/chinese_definition_drafts").glob("batch_[0-9][0-9][0-9].tsv"))
    ]
    entries: list[dict[str, object]] = []
    for category, names in EVIDENCE_FILES.items():
        for name in names:
            path = ROOT / name
            if not path.is_file():
                raise FileNotFoundError(path)
            entries.append(
                {
                    "category": category,
                    "path": name.replace("\\", "/"),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    entries.sort(key=lambda row: (str(row["category"]), str(row["path"])))

    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT / "evidence_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "evidence_set_id": "engmaster-vocabulary-provenance-20260808",
                "generated_on": "2026-08-08",
                "release_dataset": "engmaster-release-vocabulary-3800-zh",
                "repository_head_at_generation": git_head(),
                "git_commit_warning": "The repository HEAD is recorded, but this manifest does not assert that every listed file is committed. Verify git status, commit the evidence set, and create a release tag before external reliance.",
                "file_count": len(entries),
                "files": entries,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    sums_path = OUTPUT / "EVIDENCE_SHA256SUMS.txt"
    sums_path.write_text(
        "\n".join(f"{row['sha256']}  {row['path']}" for row in entries) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Wrote evidence manifest for {len(entries)} files")


if __name__ == "__main__":
    main()
