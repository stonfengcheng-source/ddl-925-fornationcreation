# EduChat 真实数据运行与复现指南

## 当前状态

200 条真实来源样本已经由用户提供的 Dataset Viewer `/rows` 响应导入，并完成命令行处理和 FastAPI HTTP 处理。详细结果见 [200 条闭环验收记录](real_data_200_report.md)。原始 Viewer 响应保留在 `data/educhat_page_0.json` 与 `data/educhat_page_100.json`；标准化 JSONL 和来源 Manifest 位于 `data/preproject/incoming/200/`。

本批是 Viewer 顺序行号 0–199，种子 `20260924` 没有用于抽样。Viewer 请求没有携带目标 revision，因此清单把 revision 和许可证的官方核验状态设为未核验。不得把本批称为精确 pinned revision 或历史固定随机样本。

## 重跑 200 条处理

在项目根目录、`good-for-all` Python 环境下：

```powershell
& 'C:\Users\wh\.conda\envs\good-for-all\python.exe' -m data_pipeline run --config configs\preproject_pipeline.json --input data\preproject\incoming\200\educhat_raw_200.jsonl --source-manifest data\preproject\incoming\200\educhat_manifest.json --data-subset-id preproject-educhat-sft-002-viewer-rows-0-199-unpinned-v1 --out-dir data\preproject\processed\educhat-200-viewer-unpinned-v1-rerun
```

使用新输出目录，因为命令默认拒绝覆盖已有处理产物。主结果包括 `processed.jsonl`、`statistics.json`、`quality_report.md` 和 `dataset_manifest.json`；另有质量指标、去重、隐私、问题样本、复核队列和运行配置文件。Manifest 会引用输入和输出文件哈希；已有结果无需反复重算哈希。

## 5,000 条下一步

5,000 条目前未获取、未处理。要继续该规模，请提供官方 Viewer/API 导出文件及其来源记录，或在有合法官方访问能力的环境中运行项目采集器。文件应放入 `data/preproject/incoming/5000/`，并保留来源行号和实际采样方式。需在采集清单中区分精确 revision、许可证核验状态、顺序分页或随机采样；顺序分页的前 5,000 条不得冒充命题书固定种子历史样本。

在来源记录与数据文件可用后，建议使用独立 subset/version ID 和输出目录运行同一命令；若只有 Viewer 文件，可以先通过 `python -m data_pipeline import-viewer-pages` 导入，具体参数参照 `python -m data_pipeline --help`。数据目录由 `.gitignore` 忽略，不应把原始教育数据提交到代码仓库。

## 验收限制

本轮没有 5,000 条样本；官方精确 revision 和许可证元数据未独立核验；没有使用浏览器（遵守用户隐私指示）；取消/失败重试尚无真实 HTTP 验收；Data-Juicer、Presidio 未集成。前端 API 连接通过代码/自动化测试验证，但浏览器实操未验收。
