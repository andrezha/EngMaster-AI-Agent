"""Export completed Chinese-definition drafts to a human-readable CSV preview."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BATCH_DIR = ROOT / "data_sources/enrichment/chinese_definition_batches"
DEFAULT_OUTPUT = (
    ROOT / "data_sources/enrichment/chinese_definition_preview_3800.csv"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_BATCH_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    output_rows: list[dict[str, str]] = []
    for path in sorted(args.batch_dir.glob("batch_[0-9][0-9][0-9].json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for record in payload["records"]:
            definitions = record["definitions_zh"]
            output_rows.append(
                {
                    "序号": record["record_id"].removeprefix("release-word-"),
                    "单词": record["word"],
                    "词性": "；".join(record["display_parts_of_speech"]),
                    "中文释义": "；".join(
                        f"{item['part_of_speech']}. {item['definition']}"
                        for item in definitions
                    ),
                    "释义状态": (
                        "AI初稿完成"
                        if record["definition_status"] == "ai_draft_complete"
                        else "待生成"
                    ),
                    "自动检查": (
                        "通过"
                        if record["qa_status"] == "automated_checks_passed"
                        else "未检查"
                    ),
                    "来源义项ID": "|".join(record["selected_source_sense_ids"]),
                    "补充说明": "；".join(record["qa_notes"]),
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    completed = sum(row["释义状态"] == "AI初稿完成" for row in output_rows)
    print(f"exported {len(output_rows)} rows; completed Chinese drafts: {completed}")


if __name__ == "__main__":
    main()
