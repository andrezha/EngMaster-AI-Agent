"""Validate explicit editorial phrase selections against approved evidence."""

from __future__ import annotations

import bz2
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELECTION_DIR = ROOT / "data_sources/editorial/phrase_master_selection"
POOL = ROOT / "data_sources/processed/phrase_candidates/four_level/candidate_pool.csv"
TATOEBA = next((ROOT / "data_sources/raw/tatoeba").glob("*.tsv.bz2"))
OUTPUT_DIR = ROOT / "data_sources/processed/phrase_selection_review"
MASTER_DIR = ROOT / "data_sources/clean/phrase_master_english"
TARGETS = {"junior": 250, "senior_high": 200, "cet4": 300, "cet6": 300}
LEVELS = tuple(TARGETS)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def phrase_type(pos_value: str) -> str:
    pos = set(pos_value.split("|"))
    if "v" in pos:
        return "verb_expression"
    if "r" in pos:
        return "adverbial_or_connector"
    if "a" in pos:
        return "adjective_expression"
    if "n" in pos:
        return "lexical_collocation"
    return "fixed_structure"


def tokens(value: str) -> list[str]:
    return re.findall(r"[a-z]+(?:'[a-z]+)?", value.casefold())


def pedagogical_key(value: str) -> str:
    """Normalize a small set of function-word variants that teach the same item."""
    parts = tokens(value)
    if parts and parts[0] == "be":
        parts = parts[1:]
    if parts == ["frown", "upon"]:
        parts = ["frown", "on"]
    key = " ".join(parts)
    audited_equivalents = {
        "rattle off": "reel off",
        "sneak away": "sneak off",
        "close down": "shut down",
    }
    return audited_equivalents.get(key, key)


def read_selections() -> dict[str, list[str]]:
    output: dict[str, list[str]] = {}
    for level in LEVELS:
        path = SELECTION_DIR / f"{level}_selected.txt"
        if path.exists():
            output[level] = [
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
    return output


def corpus_counts(phrases: set[str]) -> Counter[str]:
    counts: Counter[str] = Counter()
    ngrams = {phrase: tuple(tokens(phrase)) for phrase in phrases}
    with bz2.open(TATOEBA, "rt", encoding="utf-8") as stream:
        for raw in stream:
            columns = raw.rstrip("\n").split("\t")
            if len(columns) < 3:
                continue
            sentence = tokens(columns[2])
            for phrase, target in ngrams.items():
                size = len(target)
                if any(tuple(sentence[i : i + size]) == target for i in range(len(sentence) - size + 1)):
                    counts[phrase] += 1
    return counts


def main() -> int:
    with POOL.open(encoding="utf-8-sig", newline="") as stream:
        pool = {row["phrase"]: row for row in csv.DictReader(stream)}
    selections = read_selections()
    all_phrases = [phrase for level in selections.values() for phrase in level]
    supplemental = {phrase for phrase in all_phrases if phrase not in pool}
    supplemental_counts = corpus_counts(supplemental)

    errors: list[str] = []
    duplicate_phrases = sorted(
        phrase for phrase, count in Counter(all_phrases).items() if count > 1
    )
    if duplicate_phrases:
        errors.append(f"cross-level duplicates: {duplicate_phrases}")
    pedagogical_groups: dict[str, list[str]] = {}
    for phrase in all_phrases:
        pedagogical_groups.setdefault(pedagogical_key(phrase), []).append(phrase)
    pedagogical_duplicates = {
        key: values
        for key, values in pedagogical_groups.items()
        if len(values) > 1
    }
    if pedagogical_duplicates:
        errors.append(f"pedagogical cross-level duplicates: {pedagogical_duplicates}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    level_reports: dict[str, object] = {}
    for level, phrases in selections.items():
        if len(phrases) != TARGETS[level]:
            errors.append(f"{level}: expected {TARGETS[level]}, found {len(phrases)}")
        rows: list[dict[str, object]] = []
        for sequence, phrase in enumerate(phrases, start=1):
            candidate = pool.get(phrase)
            tatoeba_count = (
                int(candidate["tatoeba_cc0_sentence_count"])
                if candidate
                else supplemental_counts[phrase]
            )
            if candidate:
                evidence_route = "approved_dictionary_candidate_pool"
                form_evidence = "OEWN" if candidate["oewn_match"] == "true" else "Moby"
            else:
                evidence_route = "independent_structure_plus_tatoeba_cc0"
                form_evidence = "Tatoeba CC0 exact normalized occurrence"
                if tatoeba_count == 0:
                    errors.append(f"{level}: no approved evidence for {phrase!r}")
            rows.append(
                {
                    "sequence": sequence,
                    "phrase": phrase,
                    "normalized_phrase": " ".join(tokens(phrase)),
                    "introduced_level": level,
                    "evidence_route": evidence_route,
                    "form_evidence": form_evidence,
                    "oewn_pos": candidate["oewn_pos"] if candidate else "",
                    "oewn_sense_ids": candidate["oewn_sense_ids"] if candidate else "",
                    "moby_match": candidate["moby_match"] if candidate else "false",
                    "tatoeba_cc0_sentence_count": tatoeba_count,
                    "minimum_lexical_level": candidate["minimum_lexical_level"] if candidate else "manual_stage_check",
                    "editorial_status": "selected_for_cross_level_review",
                    "human_review_claimed": "false",
                }
            )
        output_path = OUTPUT_DIR / f"{level}_selection_evidence.csv"
        with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        level_reports[level] = {
            "selected_count": len(rows),
            "candidate_pool_evidence_count": sum(row["evidence_route"] == "approved_dictionary_candidate_pool" for row in rows),
            "structure_plus_corpus_count": sum(row["evidence_route"] == "independent_structure_plus_tatoeba_cc0" for row in rows),
            "zero_corpus_count": sum(int(row["tatoeba_cc0_sentence_count"]) == 0 for row in rows),
        }

    report = {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "completed_levels": list(selections),
        "level_reports": level_reports,
        "cross_level_duplicate_count": len(duplicate_phrases),
        "pedagogical_cross_level_duplicate_count": len(pedagogical_duplicates),
        "old_phrase_file_read": False,
        "human_review_claimed": False,
        "english_master_scope_frozen": len(selections) == len(LEVELS) and not errors,
    }

    if report["english_master_scope_frozen"]:
        MASTER_DIR.mkdir(parents=True, exist_ok=True)
        master_rows: list[dict[str, object]] = []
        prefixes = {"junior": "J", "senior_high": "H", "cet4": "C4", "cet6": "C6"}
        for level in LEVELS:
            evidence_path = OUTPUT_DIR / f"{level}_selection_evidence.csv"
            with evidence_path.open(encoding="utf-8-sig", newline="") as stream:
                evidence_rows = list(csv.DictReader(stream))
            for item in evidence_rows:
                sequence = int(item["sequence"])
                master_rows.append(
                    {
                        "record_id": f"PH-{prefixes[level]}-{sequence:04d}",
                        "phrase": item["phrase"],
                        "normalized_phrase": item["normalized_phrase"],
                        "accepted_variants": "[]",
                        "introduced_level": level,
                        "included_in": json.dumps(LEVELS[LEVELS.index(level) :]),
                        "phrase_type": phrase_type(item["oewn_pos"]),
                        "evidence_route": item["evidence_route"],
                        "form_evidence": item["form_evidence"],
                        "oewn_sense_ids": item["oewn_sense_ids"],
                        "moby_match": item["moby_match"],
                        "tatoeba_cc0_sentence_count": int(item["tatoeba_cc0_sentence_count"]),
                        "selection_reason": "independently selected for learning value and first-introduction level",
                        "qa_status": "english_scope_frozen",
                        "human_review_claimed": False,
                    }
                )
        csv_path = MASTER_DIR / "phrase_master_english.csv"
        json_path = MASTER_DIR / "phrase_master_english.json"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(master_rows[0]))
            writer.writeheader()
            writer.writerows(master_rows)
        json_path.write_text(
            json.dumps(master_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        master_hashes = {"csv": sha256_file(csv_path), "json": sha256_file(json_path)}
        (MASTER_DIR / "SHA256SUMS.txt").write_text(
            f"{master_hashes['csv']}  {csv_path.name}\n"
            f"{master_hashes['json']}  {json_path.name}\n",
            encoding="utf-8",
        )
        report["master_record_count"] = len(master_rows)
        report["master_sha256"] = master_hashes
    (OUTPUT_DIR / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
