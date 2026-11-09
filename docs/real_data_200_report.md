# EduChat 真实数据 200 条闭环验收记录

## 结果摘要

- **真实输入：**用户提供的 Hugging Face Dataset Viewer `/rows` 响应，`data/educhat_page_0.json` 与 `data/educhat_page_100.json`；解析并合并为 200 条连续行。原始响应文件保留。
- **来源：**`ecnu-icalk/educhat-sft-002-data-osm`，项目配置目标 split 为 `train`。
- **版本边界：**配置记录 revision `289618b953588bbd1b2a6e217cdd2c53e9cbcf49`，但 Viewer 请求未携带 revision，因而不能证明这 200 条属于该精确快照。该 revision 的官方元数据未重新核验。
- **许可边界：**`CC BY-NC 4.0` 是项目配置中的声明；Viewer 响应没有许可证元数据，未独立核验。结果只按该配置声明作本地非商业研究处理考虑，不代表获得再分发或商业使用授权。
- **抽样：**行索引 0–199 顺序分页，去掉跨页重复后共 200 条；清单记录全部行未截断。种子 `20260924` 被记录但没有用于抽样。这是新的 Viewer 顺序样本版本，不是命题书历史随机抽样的复现。
- **Gate 状态：**命令行 200 条处理通过；真实 HTTP 后端处理通过；来源快照与许可尚未独立核验，5,000 条未获取，前端未做浏览器交互验收，故整体最终验收未通过。

## 输入字段与映射

Viewer 响应实际字段为 `data`（字符串列表）和 `system_prompt`（字符串）；本批每条 `data` 有两个字符串。导入器保存 `hf_row_idx`、稳定 `sample_id` 和采集批次；映射按 `data[0::2]` 为 user、`data[1::2]` 为 assistant，最后一轮进入 `instruction` / `output`，之前完整轮次进入 `input`，`system_prompt` 进入 `system`。此角色映射依据样本位置及内容特征推断，尚无已核验的该 revision 数据说明作为独立佐证。

来源清单包含两个原始响应文件的 SHA256、行号、字段类型、采样方法、许可/版本核验状态及样本 ID。合并后原始 JSONL 的清单记录 SHA256 为：

`301acf8e0d2e1e4e47721cdb72554f911efce1bcffb082d4a31e4dfbbe4872e5`

SHA 值直接引用现有 Manifest，本记录未重新计算。

## 命令行处理

运行入口：

```powershell
& 'C:\Users\wh\.conda\envs\good-for-all\python.exe' -m data_pipeline run --config configs\preproject_pipeline.json --input data\preproject\incoming\200\educhat_raw_200.jsonl --source-manifest data\preproject\incoming\200\educhat_manifest.json --data-subset-id preproject-educhat-sft-002-viewer-rows-0-199-unpinned-v1 --out-dir data\preproject\processed\educhat-200-viewer-unpinned-v1
```

实际结果：输入/解析/输出均 200；JSON 解析错误 0；终态计数守恒 200/200（`repair=200`，`keep=0`，`review=0`，`quarantine=0`，`drop=0`）；处理耗时记录为 0.672 秒。`repair` 表示规则清理后形成的记录状态，不等同于 200 条存在实质内容错误。逐样本审计信息保存在输出记录中。

- 精确重复：0；归一化重复：0；近似重复候选：0。近重复使用 `native-simhash-v1`，阈值 3；策略为只标记复核、不自动删除。
- 隐私规则引擎：`privacy-patterns-v1`；检测到手机号、邮箱、证件号均为 0，脱敏数 0，残留复检数 0，复检通过。此结果仅代表当前规则集未命中，不是对所有类型个人信息的证明。
- 完整性：可解析率 200/200；必填字段完整率 200/200；助手目标覆盖率 200/200，均为 1.0。
- 一致性：Schema 一致率 200/200；没有重复问句组。交叉模态匹配和双人复核一致率为 N/A，因为没有多模态配对资产和双人标注。
- 多元性：启发式类别覆盖 5/5，归一化熵 `0.73975416`，近重复率 0/200。类别标签是代码内关键词规则的工程估计，不应解释为经人工确认的学科分布；长尾结果也只基于该估计分类。
- 无偏性：N/A；没有外部可靠参考分布。
- 时效性：有效发布时间覆盖率 0/200；年龄与过期比例为 N/A，缺少时间字段不被当作过期。

完整指标、分子/分母、方法、版本和不可测原因以 `quality_metrics.json`、`statistics.json` 为准。

## 真实 FastAPI 处理

用同一原始输入文件经过本地上传和 HTTP 任务处理。隔离测试环境位于 `data/preproject/api-e2e-final-real-20261029/`，实际经过上传（201）、来源列表/样本预览/验证（200）、任务创建（202）、任务完成、统计与质量结果查询（200）、版本列表查询（200）和结果下载（200）。任务重启服务后仍可读取；来源、任务和版本均保存在该次隔离数据库中。下载文件经重新解析且与任务统计相符。

CLI 与 API 使用同一条来源输入，样本数、样本 ID、输入清单 SHA、状态计数、清洗/去重/隐私计数及质量指标相同。`data_subset_id`、`source_id` 以及以来源分布为键的无偏性分组因调用来源不同而不同。CLI 输出 SHA256（Manifest 记录）：`a965050d38f53253365328c559a9b7751b6d289901a8d4bd3910462a3858eeea`；API 下载产物 SHA256（Manifest 记录）：`4f76b33417d9ee50c264812acac6783047fe8b5ecfb7c8fce89b6dadbaee773e`。两者记录的哈希不同，不能宣称整个 JSONL 字节级一致；记录的处理统计与样本 ID 集一致。

未确认授权的来源版本申请发布候选会被拒绝（HTTP 409），符合准入限制。另用独立的 `TEST-ONLY` 单样本夹具验证人工复核修改、隔离、历史和新版本生成；夹具不计入这 200 条真实数据的统计。取消和重试端点已实现，但本轮没有用真实数据执行取消/失败重试验收。

## 输出文件

命令行主产物：

- `data/preproject/processed/educhat-200-viewer-unpinned-v1/processed.jsonl`
- `data/preproject/processed/educhat-200-viewer-unpinned-v1/statistics.json`
- `data/preproject/processed/educhat-200-viewer-unpinned-v1/quality_report.md`
- `data/preproject/processed/educhat-200-viewer-unpinned-v1/dataset_manifest.json`
- 同目录另含 `quality_metrics.json`、`dedup_report.json`、`privacy_report.json`、`review_queue.jsonl`、`issue_samples.jsonl`、`run_config.json`。

FastAPI HTTP 下载产物：`data/preproject/api-e2e-final-real-20261029/downloads/`，含上述主产物和对应审计报告。原始导入文件与清单在 `data/preproject/incoming/200/`。数据目录已被 Git 忽略；原始数据没有作为源代码提交。

## 功能、测试与未完成事项

数据流水线新增 Dataset Viewer rows 解析/合并、行索引和稳定 ID、SFT 对话映射、逐样本清洗/去重/脱敏审计、N/A 质量指标、状态守恒；后端接入持久化数据资产、样本预览、任务/版本、审核和文件下载；前端页面接入来源、处理任务、结果、复核、版本和下载 API。

本轮已执行：good-for-all 下数据流水线测试 13/13；预立项页面组件测试 2/2；前端生产构建通过；指定后端路由/数据库/数据流水线 Python 编译检查通过。未使用 Edge 或其他浏览器，页面的实际人工操作流程未做视觉验收。Data-Juicer 与 Presidio 未集成；当前去重和隐私处理为项目自有兼容规则。5,000 条真实数据尚未提供/获取，不在本轮结果中。

曾有一次初始 API 测试因自定义 SQLite URL 未生效，将一条测试资产写入默认测试数据库；已定位并只清理该测试行，修正 SQLite URL 选择逻辑。最终 HTTP 验收使用独立数据库和存储目录，未删除真实数据。
