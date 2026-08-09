# 四级短语正式内容母表

本目录是冻结英文短语母表与本项目原创中文内容的机械合并结果。它不读取或改写旧产品文件 `assets/short_phrase.json`。

## 文件

- `phrase_master_content_1050.*`：1050 条统一内容母表。
- `junior_phrases_250.*`：初中累计版，250 条。
- `senior_high_phrases_450.*`：高中累计版，450 条。
- `cet4_phrases_750.*`：CET-4 累计版，750 条。
- `cet6_phrases_1050.*`：CET-6 累计版，1050 条。
- `manifest.json`：输入批次、数量、生成状态和文件哈希。
- `SHA256SUMS.txt`：正式数据文件及清单的 SHA256。

JSON 中的 `accepted_variants` 和 `included_in` 为数组，布尔字段为真正的布尔值；CSV 中数组使用 JSON 文本表示。`view_sequence` 只存在于四个累计版本中，表示该版本内的稳定顺序。

所有中文释义、用法说明和双语例句均为本项目重新编写。目前没有人工专家复核，`human_review_claimed` 必须保持为 `false`。

重新生成：

```powershell
python tools/build_phrase_master_content.py
```
