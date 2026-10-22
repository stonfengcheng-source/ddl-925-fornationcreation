# 模拟数据集 与 平台 的对接说明（ALIGNMENT）

本目录放置两份**任务二合成输入样例**，用于演示"原始数据接入 → 数据治理"在平台中的落点。
本文说明这两份 JSONL 如何与平台（`backend/app/models/dataset.py`、`schemas/dataset.py`、`api/datasets.py`）对接。

## 1. 平台数据集模型关心什么

平台的 `Dataset` 是**元数据表**，不存文件正文。创建数据集时 `POST /api/datasets` 接收的是 `DatasetCreate`：

| DatasetCreate 字段 | 含义 | 本目录数据如何填 |
|---|---|---|
| `name` | 数据集名 | 自定义，如 `教育合成语料-5k` |
| `description` | 描述 | 来源 / 领域 / 规模 |
| `data_type` | `csv/json/parquet/dicom/image` | **`json`**（JSONL 即 json 行式） |
| `row_count` | 行数 | 由文件行数得出（5000 / 300） |
| `column_count` | 字段数 | 由每行顶层键数得出（Schema v1 = 11） |
| `columns_info` | 字段说明 | 见下方 Schema v1 字段表 |
| `tags` | 标签 | `["synthetic", "education" | "government"]` |
| `quality_score` | 质量分 | 任务二治理后回写（见第 3 节） |
| `node_id` / `owner_id` | 归属 | 平台登录后由后端填 |

**关键点**：平台按 `data_type=json` 入库元数据，文件本身另存（本地磁盘 / 对象存储）。本目录的 `.jsonl` 即是"待入库的原始文件"，与平台约定的 `json` 类型一致，无需格式转换。

## 2. Schema v1 字段（每行 JSONL）

| 字段 | 类型 | 说明 |
|---|---|---|
| `sample_id` | string | 全局唯一主键（任务一分配，不可改写） |
| `modality` | string | 模态，文本为 `text` |
| `raw_text` | string | 原始文本，**写入后不可变** |
| `meta` | object | 来源元数据（source_id / license / domain / category / crawl_time …） |
| `clean_text` | string | 清洗结果；原始输入态等于 `raw_text` |
| `masked_text` | string | 脱敏结果；原始输入态等于 `raw_text` |
| `hash` | object | `{exact, simhash}`，治理阶段填充 |
| `flags` | object | 规则命中 / 去重簇 / PII / 决策等标记 |
| `decision` | string | `keep` / `review` / `drop` |
| `version` | string | Schema 版本 `v1` |
| `stage_trace` | array | 处理轨迹 |

字段均为平台无关的普通 JSON 标量 / 对象，可直接被 Python `json` 解析并映射到 `columns_info`。

## 3. 任务二治理产出 如何回流平台

任务二跑完后会产出 `clean_text` / `masked_text` / `flags` / `decision` / `quality_score` 等。
回流方式（二选一，取决于平台后续是否接文件内容）：
- **元数据回流**：把 `row_count`、`column_count`、`quality_score`、`tags` 通过 `PUT /api/datasets/{id}` 写回对应 Dataset 记录；`quality_score` 可直接驱动前端"质量报告"页面。
- **文件回流**：治理后的 JSONL 作为新版本文件另存，重新注册为一个 `data_type=json` 数据集（保留 `raw_text` 用于溯源）。

## 4. 注册示例（本地起平台后）

```bash
# 先本地启动平台（见仓库 README 的 start-dev.bat），登录 admin
curl -X POST http://127.0.0.1:8000/api/datasets \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "教育合成语料-5k",
    "description": "任务二教育领域合成输入样例，5000 条，license=synthetic",
    "data_type": "json",
    "row_count": 5000,
    "column_count": 11,
    "tags": ["synthetic", "education", "task2-demo"],
    "columns_info": ["sample_id","modality","raw_text","meta","clean_text","masked_text","hash","flags","decision","version","stage_trace"]
  }'
```

## 5. 校验

`validate_alignment.py` 静态校验两份 JSONL：逐行合法 JSON、顶层键齐备、可派生 `row_count` / `column_count` / `columns_info`，并输出可直接作为 `DatasetCreate` 入参的载荷。运行：

```bash
python validate_alignment.py
```
