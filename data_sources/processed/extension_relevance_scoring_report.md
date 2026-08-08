# 扩展词高中学习相关性评分报告

## 核心结论

本轮对第一轮筛查通过的 1007 个普通扩展词进行独立频率评分。ECDICT 只提取精确词形、BNC 排名、当代语料排名和审计标签；不提取、不输出中文释义、英文释义、音标、例句及音频字段。

- ECDICT 精确或大小写匹配：1007/1007
- 带 ECDICT `gk` 标签：995/1007（98.8%）
- 带自动词形复核标记：69

`gk` 标签与旧候选表重合过高，表明二者可能同源或曾相互引用。为避免循环论证，`gk`、`zk`、`cet4`、Oxford、Collins 等标签均不计入本轮分数。

## 评分规则

BNC 和当代语料分别计分：排名 1–5000 得4分，5001–10000得3分，10001–20000得2分，20001–40000得1分，缺失或超过40000得0分；两套语料都有有效排名再加1分。总分0–9。

- 7–9分：频率支持较强，作为拓展词优先候选。
- 4–6分：进入高中阅读主题和词形二次复核。
- 0–3分：没有更多独立证据前暂不纳入。

频率高不等于一定适合高中教学；频率低也不等于词本身错误。本结果是可复算的机器分层，不是最终发布清单。

## 分档结果

| 建议 | 数量 | 示例 |
| --- | ---: | --- |
| frequency_supported_extension | 737 | abolish、abortion、abrupt、absolute、absurd、abundant、academy、accelerate、accessible、accomplish、accountant、accumulate、accuracy、accustomed、acquaintance |
| secondary_relevance_review | 218 | acre、admirable、aeroplane、airplane、airspace、algebra、allergic、alphabet、aluminium、amaze、arithmetic、astronomy、attentively、bacterium、bandage |
| hold_without_more_evidence | 52 | addicted、airmail、backache、ballpoint、barbershop、bedclothes、birdcage、bookmark、centigrade、changeable、customs、dictation、eastwards、eggplant、firework |

## 频率画像

| 画像 | 数量 |
| --- | ---: |
| limited_frequency | 23 |
| mixed_between_corpora | 30 |
| moderate_frequency | 98 |
| no_frequency_rank | 4 |
| single_corpus_only | 30 |
| strong_in_both_corpora | 724 |
| strong_with_moderate_cross_corpus_support | 98 |

## 分数分布

| 分数 | 数量 |
| ---: | ---: |
| 0 | 5 |
| 1 | 5 |
| 2 | 11 |
| 3 | 31 |
| 4 | 46 |
| 5 | 76 |
| 6 | 96 |
| 7 | 239 |
| 8 | 129 |
| 9 | 369 |

## 下一步

先对中档和词形标记项进行规则化处理，再按高中阅读主题（人与自我、人与社会、人与自然及常见学科阅读）补充收录理由。只有具备明确理由的词才进入最终 `extension` 层。
