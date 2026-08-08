# 不规则动词表清洗审计报告

- 生成日期：2026-08-08
- 旧表候选词头：126（仅作待核对索引）
- 新表记录：126
- 进入3800独立词表：121
- 项目独立补充释义：5
- 自动校验错误：0
- 人工专家审核声明：无

## 来源边界

旧文件 `assets/irregular_verbs.json` 只用于确定需要核对的126个原形。新表没有读取或继承旧表的过去式、过去分词和中文释义。词形证据来自 Open English WordNet 2025 的 `verb.exc`，同形不规则变化和规则并存变体按明确规则记录；中文释义优先来自本项目独立制作的3800词表。

## 与旧表的词形展示差异

- **be**：过去式：`was, were` → `was / were`
- **bet**：过去式：`bet` → `bet / betted`；过去分词：`bet` → `bet / betted`
- **burn**：过去式：`burned, burnt` → `burned / burnt`；过去分词：`burned, burnt` → `burned / burnt`
- **can**：过去分词：`-` → `—`
- **dream**：过去式：`dreamed, dreamt` → `dreamed / dreamt`；过去分词：`dreamed, dreamt` → `dreamed / dreamt`
- **get**：过去分词：`got` → `got / gotten`
- **hang**：过去式：`hung, hanged` → `hung / hanged`；过去分词：`hung, hanged` → `hung / hanged`
- **learn**：过去式：`learned, learnt` → `learned / learnt`；过去分词：`learned, learnt` → `learned / learnt`
- **light**：过去式：`lit, lighted` → `lit / lighted`；过去分词：`lit, lighted` → `lit / lighted`
- **may**：过去分词：`-` → `—`
- **must**：过去式：`must` → `—`；过去分词：`-` → `—`
- **rid**：过去式：`rid, ridded` → `rid / ridded`；过去分词：`rid, ridded` → `rid / ridded`
- **shall**：过去分词：`-` → `—`
- **shine**：过去式：`shone, shined` → `shone / shined`；过去分词：`shone, shined` → `shone / shined`
- **show**：过去分词：`shown, showed` → `shown / showed`
- **sink**：过去式：`sank, sunk` → `sank / sunk`
- **smell**：过去式：`smelled, smelt` → `smelled / smelt`；过去分词：`smelled, smelt` → `smelled / smelt`
- **sow**：过去分词：`sown, sowed` → `sown / sowed`
- **spell**：过去式：`spelled, spelt` → `spelled / spelt`；过去分词：`spelled, spelt` → `spelled / spelt`
- **spill**：过去式：`spilt` → `spilled / spilt`；过去分词：`spilt` → `spilled / spilt`
- **spit**：过去式：`spat` → `spat / spit`；过去分词：`spat` → `spat / spit`
- **spoil**：过去式：`spoilt` → `spoiled / spoilt`；过去分词：`spoilt` → `spoiled / spoilt`
- **strike**：过去分词：`struck, stricken` → `struck / stricken`
- **swell**：过去分词：`swollen` → `swollen / swelled`
- **wake**：过去式：`woke, waked` → `woke / waked`；过去分词：`woken, waked` → `woken / waked`
- **weave**：过去式：`wove` → `wove / weaved`；过去分词：`woven` → `woven / weaved`
- **will**：过去分词：`-` → `—`

这些差异不表示旧表全部错误，主要是补充可接受变体、统一斜线两侧空格，以及把没有过去分词的情态动词明确标成“—”。
