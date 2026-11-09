# EduChat 数据来源与获取状态

## 已获取的 200 条样本

- 数据集标识：`ecnu-icalk/educhat-sft-002-data-osm`；目标 split 声明为 `train`。
- 实际输入：用户提供的两份 Dataset Viewer `/rows` 响应 `data/educhat_page_0.json`、`data/educhat_page_100.json`。两页解析出行索引 0–199，合计 200 条；索引连续且无重复；每条 Viewer row 没有 `truncated_cells`。
- 原始字段：`data`（本批均为两个字符串的列表）和 `system_prompt`（字符串）。标准化文件保留原行索引为 `hf_row_idx`，生成样本 ID，并保留多轮数据字段。
- 标准化文件：`data/preproject/incoming/200/educhat_raw_200.jsonl`，200 行。来源清单：`data/preproject/incoming/200/educhat_manifest.json`；另有 `collection_log.jsonl` 和 `import_log.jsonl`。
- 原始 JSONL SHA256（读取自已有 Manifest，未重新计算）：`301acf8e0d2e1e4e47721cdb72554f911efce1bcffb082d4a31e4dfbbe4872e5`。
- 采样方法：Viewer offset 0 和 100 顺序分页；配置种子 `20260924` 仅记录、未使用。

## 版本、许可与来源真实性边界

目标 revision `289618b953588bbd1b2a6e217cdd2c53e9cbcf49` 是项目配置声明。实际 Viewer 请求没有 revision 参数，不能声称该批已绑定此版本。项目配置声明 `CC BY-NC 4.0`，但 Viewer 响应没有许可证元数据；本地 Manifest 明确 `license_verified=false`、`revision_verified=false`。输入文件结构、行号和本地文件哈希已校验；来源端独立认证状态为 false。不能据此推定商业使用或再分发授权。

## 处理与验收

200 条已完成 CLI 和实际 FastAPI HTTP 处理，完整结果、质量指标、API 证据及限制见 `docs/real_data_200_report.md`。5,000 条尚未取得。不要将已完成的 200 条工程样本描述为历史随机采样样本。
