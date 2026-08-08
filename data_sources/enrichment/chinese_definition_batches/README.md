# 中文释义重建工作批次

本目录把 3,800 条发布词目按固定顺序拆成每批 100 条，共 38 批。批次保存开放来源的英文语义证据、词性证据、独立中文释义及自动检查状态，不含旧词表中文释义。当前38批已经全部完成并通过自动检查。

## 编写规则

1. 先选择适合中学学习的英文义项，再用自己的中文表述写简洁释义；不得逐项机械翻译全部 WordNet 义项。
2. `selected_source_sense_ids` 记录采用的 OEWN sense ID；没有 OEWN 义项时，必须在 `qa_notes` 记录补充判断依据。
3. `definitions_zh` 中每项使用结构 `{"part_of_speech": "...", "definition": "..."}`。
4. `display_parts_of_speech` 只保留最终展示需要的词性，不能照搬来源里所有历史或生僻词性。
5. 完成初稿后将 `definition_status` 改为 `ai_draft_complete`；通过自动检查后再改 `qa_status`，不得直接标记人工审核。

## 风险控制

- 不读取、不复制 `assets/vocabulary.json` 的中文释义、音标或例句。
- 不使用 ECDICT 的 translation 字段。ECDICT 在前一阶段仅用于词目存在性核对。
- OEWN 义项是候选证据，不保证覆盖冠词、介词、连词等教学常用语法义。例如 `a` 可能只匹配到字母名词义，因此所有词都必须经过义项选择。
- `no_oewn_semantics_requires_controlled_research` 项目需要单独补充可说明的判断依据。

批次文件由 `tools/prepare_chinese_definition_batches.py` 可重复生成，输入文件哈希和每批哈希见 `batch_manifest.json`。

## 完成状态

- 中文释义完成：3800/3800
- 自动检查通过：3800/3800
- 自动校验：0错误、0警告
- 人工审核声明：无；当前状态只表示独立初稿通过自动检查
