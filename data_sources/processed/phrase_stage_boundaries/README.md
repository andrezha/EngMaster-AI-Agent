# 三级短语项目词汇边界

本目录是初中、高中、CET-4短语分级使用的范围证据，不是短语表，也不是产品词汇表。

## 文件

- `high_school_2025_entries.csv`：2025高中课标附录2实际印刷条目及星号；
- `cet_2016_word_family_lines.csv`：CET大纲词表按页面视觉基线重建的词族行；
- `phrase_stage_vocabulary_tokens.csv`：从上述印刷条目保守拆出的规范化词形及最早文档层级；
- `validation.json`：数量、来源内部差异和“未读取旧短语表”声明；
- `SHA256SUMS.txt`：生成文件校验值。

## 使用边界

短语分级时，组成词命中本表只是层级证据之一，不能自动决定短语是否收录。形式成立仍需OEWN/Moby/Tatoeba等已批准开放证据，中文释义和产品例句仍须独立创作。

2025高中课标说明声明3100词，但正文实际印刷3099条；CET大纲声明5418个“词目”，而本项目按视觉基线得到5377个词族行。这些差异均保留并解释，没有靠猜测补齐。

重新生成命令（环境须安装 `pypdf` 和 `cryptography`）：

```powershell
python tools\extract_phrase_stage_vocab_boundaries.py
```
