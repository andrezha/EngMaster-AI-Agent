# 干净课标词汇底座

本目录保存从教育部《普通高中英语课程标准（2017年版2020年修订）》附录2独立生成的新词库底座。

## 数量口径

- 官方来源条目：3000条。
- 应用层原子学习记录：3004条。

数量相差4，是因为官方表中以下4条使用 `/` 合并两个不同词，本项目为避免识别错误并允许分别制作释义，将它们拆成8条原子记录：

- `bride / bridegroom`
- `chairman / chairwoman`
- `policeman / policewoman`
- `salesman / saleswoman`

拆分后的记录继续共享原始 `source_sequence`，因此仍能完整回指官方3000条母表。对外说明课标范围时使用“官方来源3000条”；应用内部统计学习记录时可以说明为3004条。

## 文件

- `curriculum_base.json`：后续释义和音标加工使用的主文件。
- `curriculum_base.csv`：便于筛选和人工查看的表格版本。
- `curriculum_base_manifest.json`：生成方式、数量校验、来源哈希和内容政策。
- `SHA256SUMS.txt`：生成文件哈希。

## 初始字段规则

- `word`：应用使用的单一学习词，不包含 `/` 和括号说明。
- `official_variants`：官方括号中的美式拼写、简称、复数或其他形式。
- `source_entry`：官方附录原始条目，保留括号和斜杠供审计。
- `source_sequence`：官方3000条母表序号。
- `source_component_index`：组合条目拆分后的序号；普通条目固定为1。
- `curriculum_level`：依据PDF实际印刷星号映射的层级。
- `part_of_speech`、`definitions_zh`、`phonetic_uk`、`phonetic_us`：初始为空，后续只从已确定的开放来源补充。
- `enrichment_status`：当前统一为 `pending_definition_and_phonetics`。

## 内容隔离

生成脚本只读取课标母表，不读取 `assets/vocabulary.json`，因此本目录没有复制旧词库的中文释义、音标、排序或分组。

重新生成命令：

```powershell
.\.venv\Scripts\python.exe .\tools\build_clean_curriculum_base.py
```
