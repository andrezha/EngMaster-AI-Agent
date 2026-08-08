# 扩展词词形处理与收录理由报告

## 词形处理

本轮复核 78 个带词形标记的项目。机器只依据课标母表和 OEWN 独立词头记录作处理建议，不使用旧中文释义。

| 处理建议 | 数量 |
| --- | ---: |
| exclude_redundant_inflection_of_curriculum | 6 |
| keep_confirmed_independent_lemma | 68 |
| move_to_special_reference_review | 1 |
| replace_with_normalized_extension_headword | 3 |

规范化后产生的新扩展词头：
- `beddings` → `bedding`：secondary_relevance_review，评分 6/9
- `refreshments` → `refreshment`：secondary_relevance_review，评分 6/9
- `souvenirs` → `souvenir`：frequency_supported_extension，评分 7/9

## 主题收录理由

OEWN 的 lexicographer class 被映射为“人与自我、人与社会、人与自然、一般阅读”的候选标签。一个词可以有多个候选主题。该映射只用于缩小复核范围，不能替代最终义项判断。

| 主题候选 | 数量（可重复） |
| --- | ---: |
| 一般阅读 | 196 |
| 人与社会 | 656 |
| 人与自我 | 260 |
| 人与自然 | 306 |

## 使用边界

- 独立收录理由只引用语料频率、OEWN 词性和语义类别。
- ECDICT 的 `gk` 等考试标签不参与分数或收录理由。
- 当前主题均标记为 `machine_candidate_needs_review`，尚未宣称人工确认。
- 本轮没有修改正式词库。
