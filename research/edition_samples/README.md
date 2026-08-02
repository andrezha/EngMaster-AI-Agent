# 多版本词表开发样本

这里的 JSON 仅用于验证中考、大学四级、大学六级的多版本数据架构，
不参与当前正式版打包，也不应直接作为商业正式词库发布。

## 样本来源

- `zhongkao_sample.json`：`ZhongKaoHeXin.json`
- `cet4_sample.json`：`CET4_T.json`
- `cet6_sample.json`：`CET6_T.json`

源文件来自本地 Qwerty Learner 仓库。该仓库使用 GPLv3，README 同时说明
其字典数据来自外部抓取字典。正式商用前必须另外核实每套词表及释义数据的
来源、授权范围和署名/开源义务；未经核实，不应把这些样本作为正式产品数据。

每套样本固定为 30 个词，字段已经转换为当前项目可继续演进的统一格式：

- `id`
- `word`
- `pronunciation`
- `content`
- `edition`
- `source`
- `data_status`

重新生成命令：

```powershell
python tools/build_edition_sample_vocab.py "D:\软件词库\qwerty-learner\public\dicts"
```
