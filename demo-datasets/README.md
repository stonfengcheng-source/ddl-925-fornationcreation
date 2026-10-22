# demo-datasets（任务二模拟数据集）

本目录存放**任务二（数据清洗 / 去重 / 脱敏）的合成输入样例**，用于演示"原始数据接入 → 治理"在平台中的落点。

| 数据集 | 路径 | 规模 | 领域 | 许可 |
|---|---|---|---|---|
| 教育合成语料 | `education-synthetic/raw_5k.jsonl` | 5000 条 | 教育（数学/语文/英语） | synthetic |
| 政务合成演示语料 | `government-synthetic/gov_synthetic_300.jsonl` | 300 条 | 政务（社保/公积金/营业执照/户籍/税务） | synthetic |

两份均为**原始输入态**（尚未治理），字段遵循 Schema v1，详见 [`ALIGNMENT.md`](./ALIGNMENT.md)。

- **合规说明**：两份均为本地合成、许可 `synthetic`，不含任何真实个人信息或受版权约束的文本，**可安全放入本公开仓库**。任务二外部验证所用的真实公开语料（COIG-CQIA / CLUE-NER）不在此目录，也不进入公开交付。
- `government-synthetic/generate_synthetic_gov.py`：政务语料生成脚本（确定性，种子 4471）。
- `validate_alignment.py`：对接校验，验证两份 JSONL 可作为 `data_type=json` 数据集注册到平台。
