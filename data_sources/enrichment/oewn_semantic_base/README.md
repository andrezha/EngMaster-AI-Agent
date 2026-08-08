# 3800词 OEWN 英文语义底稿报告

## 用途边界

本底稿从 Open English WordNet 2025 提取词头、词性、synset、英文义项和 lexicographer class，用作后续中文释义的语义依据。它不是最终中文词库；没有使用旧中文释义，也没有生成音标。

- 发行记录：3800
- 获得词性证据：3695
- 获得至少一个OEWN义项：3695
- 待其他来源补充：105

## 匹配方式

| 匹配状态 | 数量 |
| --- | ---: |
| casefold_headword | 4 |
| exact_headword | 3689 |
| exact_variant | 2 |
| no_oewn_match | 105 |

## 分层覆盖

| 数据层 | 状态 | 数量 |
| --- | --- | ---: |
| curriculum | needs_non_oewn_review | 99 |
| curriculum | oewn_semantic_base_ready | 2905 |
| extension | needs_non_oewn_review | 6 |
| extension | oewn_semantic_base_ready | 790 |

## 许可证

Open English WordNet 2025 的OEWN部分使用 CC BY 4.0，并要求同时保留 Princeton WordNet 和 Open English WordNet Team 的署名。完整许可证见 `data_sources/raw/oewn/LICENSE.md` 及项目第三方声明。

## 下一步

无OEWN义项或大小写敏感未匹配项进入Moby/ECDICT词性补充清单；有多个义项的词在生成中文释义时按高中适用性筛选，不能把全部专业义项机械翻译。
