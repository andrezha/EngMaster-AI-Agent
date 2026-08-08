# 现有扩展词候选第一轮筛查报告

## 结论边界

本轮只检查词形结构，以及 OEWN 2025、Moby Words II / Moby Part-of-Speech II 是否收录。词典收录只能证明候选有一定词汇证据，不能证明它适合高中阶段，也不能自动进入发布词库。未复制旧词库的中文释义、音标或例句。

- 候选唯一词形：1204
- 已在现有短语表中找到同形短语：0

## 按结构分组

| 结构 | 数量 |
| --- | ---: |
| all_uppercase | 8 |
| hyphenated | 41 |
| initial_uppercase | 43 |
| lowercase_single_word | 1049 |
| multiword | 63 |

## 初筛建议

| 建议 | 数量 | 示例 |
| --- | ---: | --- |
| exclude_or_spelling_review | 2 | handtruck、headteacher |
| hyphenated_form_review | 41 | best-seller、co-worker、cold-blooded、dining-room、easy-going、get-together、hide-and-seek、kind-hearted、left-handed、left-wing、letter-box、man-made |
| inflected_form_review | 9 | beddings、cheers、does、grandparents、refreshments、regards、repairs、skipping、souvenirs |
| legacy_lexicon_review | 10 | hey、oh、oneself、ouch、ought、theirs、via、videophone、whichever、yourselves |
| modern_lexical_review | 21 | battleground、bodybuilding、bookshop、chips、firefighter、founding、furnished、judgement、microcomputer、nursing、organiser、pleased |
| move_to_phrase_review | 63 | bank account、boat race、bus stop、can opener、card games、chain store、cheer up、Christmas card、Christmas Eve、Christmas tree、computer game、department store |
| proper_name_or_capitalization_review | 43 | Antarctic、Antarctica、Arab、Arabic、Arctic、Belgium、Buddhism、Buddhist、Christian、Dr、Easter、Egypt |
| retain_for_relevance_scoring | 1007 | abolish、abortion、abrupt、absolute、absurd、abundant、academy、accelerate、accessible、accomplish、accountant、accumulate |
| special_reference_review | 8 | AIDS、CD、CD-ROM、DVD、P.C.、UN、USA、VCD |

## 开放词汇证据数量

| 命中的数据集数（0–3） | 数量 |
| ---: | ---: |
| 0 | 41 |
| 1 | 47 |
| 2 | 87 |
| 3 | 1029 |

## 数据来源

- Open English WordNet 2025 标准版；CC BY 4.0。未使用专名补充包。
- Moby Words II 与 Moby Part-of-Speech II；作者已作公有领域授权声明。
- `assets/short_phrase.json` 仅用 `p` 字段检查已有短语是否同形，不读取或输出中文释义和例句内容。

## 下一步

对 `retain_for_relevance_scoring` 和其他人工复核桶建立可解释的学习相关性评分，再决定保留哪些扩展词。短语、专名/缩写、连字符形式分别处理，不直接混入单词母表。
