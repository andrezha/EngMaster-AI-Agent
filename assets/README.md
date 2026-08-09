# 运行数据目录

正式发行数据统一放在 `assets/editions/<edition_id>/` 下，不再从 `assets` 根目录读取旧版单词、短语或不规则动词表。

当前完整版本为 `assets/editions/gaokao/`：

- `vocabulary.json`：3800 个单词
- `phrases.json`：450 个短语（核心 300、扩展 150）
- `irregular_verbs.json`：126 组不规则动词
- `manifest.json`、校验报告、哈希和许可证文件：用于说明版本、校验数据和保留第三方许可声明

`vocabulary_progress_aliases.json` 是旧学习进度迁移所需的共享映射，不是旧词表，因此继续保留。

旧版根目录数据及早期高中短语、不规则动词样本已在新版数据冻结后移除。制作依据、清洗记录、来源声明和许可材料保存在 `data_sources/`，已提交的旧文件也可从 Git 历史追溯。

用户学习进度、错词和自定义词汇属于运行时个人数据，应保存在程序的数据目录中，不应作为发行资源打包进 EXE。
