# 短语中文内容编制批次

本目录用于在冻结的英文短语母表之上，逐批编制原创中文释义、中文用法说明以及原创中英文例句。

## 数据边界

- 英文条目唯一来源：`data_sources/clean/phrase_master_english/phrase_master_english.json`
- 不读取、不改写产品旧文件 `assets/short_phrase.json`
- 中文释义、用法说明和双语例句均为本项目重新编写
- 当前没有人工专家复核，因此所有记录必须保留 `human_review_claimed=false`

## TSV 字段

`record_id`、`phrase`、`meaning_zh`、`usage_note_zh`、`example_en`、`example_zh`、`content_method`、`qa_status`、`human_review_claimed`。

每批完成后运行：

```powershell
python tools/validate_phrase_content_batches.py
```

