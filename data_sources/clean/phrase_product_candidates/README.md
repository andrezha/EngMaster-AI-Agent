# 产品格式候选短语文件

本目录把四个累计短语版本映射为 EngMaster 当前短语模块所需的 `p/m/en/cn/answers/tier/level` 结构。

旧文件 `assets/short_phrase.json` 只用于确认字段名称和程序兼容行为，其短语、中文、例句和排序均未复用。候选文件尚未写入 `edition_config.py`，也未覆盖任何正式产品资源。

所有条目暂标为 `core`，每 50 条组成一个稳定关卡。四个候选版本分别形成 5、9、15、21 个关卡。

生成和验证：

```powershell
python tools/build_phrase_product_candidates.py
python tools/validate_phrase_product_candidates.py
```
