# 第四模块 数据筛选与模型效果验证

本目录完成教育文本 MVP（最小可用产品）的第四模块：生成 Raw、Rule、LLM-only、Data-Juicer、Ours 五组等量训练数据，使用同一基础模型进行 LoRA（低秩适配）微调，通过 OpenCompass 在 C-Eval、CMMLU 等独立 Benchmark（基准测试集）上统一评测，并把错误样本回流给任务二和任务三。

## 在现有平台网页中使用

模块4已接入原有 React / FastAPI 平台，页面入口为侧栏的 **数据筛选与模型验证**（`/app/module4`）。
沿用项目原来的前后端启动方式，例如 `scripts/start-dev.bat`，在 `http://localhost:5173` 使用 `admin` 或买方账号登录即可操作。无需单独启动模块4服务。

页面支持环境检查、五组数据生成与校验、训练配置、LoRA 微调、模型合并、评测配置、试运行、正式评测、重新评分和结果汇总。离开页面不会停止任务，返回后可继续查看日志或停止任务。

训练环境优先使用项目根目录的 `.venv-lora`。也可在页面的“训练 Python”字段指定已有环境的 python.exe 完整路径，无需复制或移动虚拟环境。留空且不存在 `.venv-lora` 时使用平台后端解释器，实际训练前应先点击环境检查确认依赖。

OpenCompass 使用页面指定的独立评测环境和纯英文工作目录。可搜索、多选 C-Eval 的 52 个科目与 CMMLU 的 67 个科目，自选每科题量（1～10000 题）或使用所选科目的全部题目；所有模型保持相同的评测科目与题量。

快捷档位依次为极简（2 科×5 题）、快速（4 科×10 题）、轻量（6 科×15 题）、标准（8 科×20 题）、扩展（10 科×25 题）、深入（12 科×30 题），另提供完整评测（119 科、全部题目）。题量均为上限，实际不超过各科题库大小。选择档位后仍可调整科目和题量，页面会自动切换为自定义。

科目与档位共用 `configs/module4/evaluation_options.json`，科目名称取自 OpenCompass 的 C-Eval 与 CMMLU 配置。命令行自定义示例：`python scripts/module4/04_make_eval_manifest.py --base-model Qwen/Qwen2.5-0.5B-Instruct --variants --eval-mode custom --subjects ceval:computer_network cmmlu:education --samples-per-subject 10`。将 `--samples-per-subject 10` 换为 `--all-questions` 可使用所选科目的全部题目。

技术说明见 [INTEGRATION.md](INTEGRATION.md)，操作说明见 [模块4网页使用说明.md](../../模块4网页使用说明.md)。

## 提交到 GitHub

提交模块4源码、测试、平台路由与权限接入、文档、通用启动脚本，以及 `configs/module4/evaluation_options.json`（科目目录与快捷档位）。`.env.example` 只保存不含真实凭据的配置说明。

以下文件保留在本地，由 `.gitignore` 排除：真实 `.env`、虚拟环境、依赖目录、模型权重、实验输出、日志、缓存，以及 `configs/module4` 下生成的训练/合并 YAML、数据注册与数据副本、训练清单、运行批处理文件。这些产物包含本机绝对路径或可重新生成的数据，队友应在自己的电脑上通过网页重新生成。未经授权的真实业务数据、密钥和个人信息也不应上传。

## 一 当前代码完成情况

当前自带训练集的具体题目、各组样本与来源见 [TRAINING_DATA.md](TRAINING_DATA.md)。

训练配置会按预计优化器步数限制预热步数，确保至少有一个非零学习率更新步。训练结束后检查 LoRA B 矩阵是否产生更新，全零适配器会报错并阻止模型合并。模型导出时保留 Transformers 4/5 都可读取的 `rope_theta`、`rope_scaling` 和 `torch_dtype`；评测明确指定所有模型相同的推理精度与非采样生成设置。

评测采用协议 v3，按评测模式、科目与题量指纹、输出长度和精度隔离预测与模型配置目录，汇总与重新评分均使用当前清单指定的目录。默认每题最多输出 512 token，所有模型统一使用该限制。调整科目、题量或输出长度后，重新生成评测配置并执行“开始评测”，再汇总结果；已有模型可以继续使用，无需为此重新训练或合并。升级前生成的评测清单也需要重新生成。

| 步骤 | 脚本 | 状态 |
|---|---|---|
| 环境检查 | `00_check_environment.py` | 可检查 Python、训练包、CUDA 和命令是否可用 |
| 评测依赖修复 | `09_fix_opencompass_dependencies.py` | 固定兼容的 Transformers 版本并检查分词接口 |
| 等量数据生成 | `01_build_datasets.py` | 支持五组对照，固定随机种子并记录哈希 |
| 数据验收 | `02_validate_dataset.py` | 检查数量、字段、ID、重复和五组等量性 |
| LoRA 配置 | `03_prepare_llamafactory.py` | 自动生成数据注册、训练配置、模型合并配置和批处理文件 |
| 统一评测 | `04_make_eval_manifest.py` | 自动生成 Base 与五组微调模型的 OpenCompass 命令 |
| 结果汇总 | `05_compare_results.py` | 自动读取六个评测对象的最新OpenCompass评分并生成统一比较表 |
| 错误回流 | `06_badcase_template.py` | 输出任务二、任务三可复查的错误样本 |

JSONL 是“每行一个 JSON 对象”的文件格式；Mean 是平均值；Std 是标准差；Delta Score 是微调模型分数减去基础模型分数。

## 二 数据接口

未接入的上游结果可以留空。网页默认仅使用 5000 条教育原始候选文本生成 Raw 验证数据；Rule、LLM-only、Ours 等待质量评价结果，Data-Juicer 等待独立处理结果。缺失组记入清单的 `pending_variants`，不生成空训练文件，不参与校验、训练或评测。后续流程只读取当前清单中的可用组，忽略遗留的同名文件和缺失组旧分数。

原始候选池至少需要：

```json
{"id":"edu_000001","question":"题目","answer":"答案"}
```

质量评价结果建议使用：

```json
{
  "id": "edu_000001",
  "question": "题目",
  "input": "可选上下文",
  "answer": "答案",
  "subject": "数学",
  "rule_pass": true,
  "decision": "keep",
  "quality_score": 0.91,
  "task_match_score": 0.86,
  "coverage_score": 0.75
}
```

问题字段兼容 `instruction/question/prompt/query`，答案字段兼容 `output/answer/response/target`，上下文字段兼容 `input/context`。每条样本必须有唯一 `id`。

同时支持仓库 `demo-datasets/education-synthetic/raw_5k.jsonl` 的 Schema v1：用 `sample_id` 作为统一 ID，从 `raw_text` 中拆分“题目：… / 答案：… / 解析：…”，将题目作为 `instruction`、答案和可选解析作为 `output`。兼容 HTML 段落及中英文冒号；缺少问答时仍会报错。`raw_text` 为空时可读取 `clean_text` 或 `masked_text`，已有独立问答字段优先。学科覆盖统计兼容 `meta.subject`。

Data-Juicer 组还必须提供独立流水线的真实输出文件。它可以只保留处理后通过的样本，但每条记录仍需包含唯一 `id`、问题和答案。不能把 Rule 输出复制一份并命名为 Data-Juicer。

五组使用同一件事进行对比：

| 版本 | 对同一批教育问答做什么 |
|---|---|
| Raw | 固定随机抽取，保留原始内容重复，用作不治理的底线 |
| Rule | 仅保留规则通过样本，精确去重后随机抽取 |
| LLM-only | 不使用规则，仅按大模型 `quality_score` 单一总分取 Top-K |
| Data-Juicer | 从 Data-Juicer 独立处理结果中精确去重后随机抽取 |
| Ours | 规则通过且大模型判断为 keep，再按质量、任务匹配和覆盖分进行学科平衡选择 |

## 三 先检查本地环境

在项目根目录运行：

```powershell
.\.venv-lora\Scripts\python.exe scripts\module4\00_check_environment.py
```

训练至少需要 `torch`、`transformers`、`datasets`、`peft`、`llamafactory` 和 `llamafactory-cli`。CUDA 是统一计算设备架构，用于让 PyTorch 调用 NVIDIA 图形处理器。检查脚本还会调用 `nvidia-smi` 读取显卡名称、显存和驱动版本，并写入 `experiments/module4/environment_report.json`。

各电脑的训练依赖以页面“检查训练环境”的输出为准。不要把 `.venv-lora` 提交到 Git。

## 四 使用仓库教育原文验证数据接口

默认从仓库的 5000 条教育文本中抽取 100 条 Raw 数据，质量评价和独立清洗结果等待队友模块接入：

```powershell
.\.venv-lora\Scripts\python.exe scripts\module4\01_build_datasets.py `
  --raw demo-datasets\education-synthetic\raw_5k.jsonl `
  --n 100 --seed 42

.\.venv-lora\Scripts\python.exe scripts\module4\02_validate_dataset.py --n 100
```

输出 `raw_100.jsonl` 和对应清单、校验报告。Rule、LLM-only、Data-Juicer、Ours 保留为待接入状态；不生成这些组的占位训练数据。

## 五 生成正式的五组 2000 条数据

```powershell
.\.venv-lora\Scripts\python.exe scripts\module4\01_build_datasets.py `
  --raw path\to\raw_5k.jsonl `
  --evaluated path\to\quality_eval_5k.jsonl `
  --datajuicer path\to\datajuicer_5k.jsonl `
  --n 2000 --seed 42

.\.venv-lora\Scripts\python.exe scripts\module4\02_validate_dataset.py --n 2000
```

除五组训练数据外，还会生成：

- `dataset_manifest_2k.json`：来源、选择标准、数量、文件哈希、样本 ID 哈希和学科分布；
- `selection_audit_2k.jsonl`：每条入选数据所属版本、排名和评分；
- `validation_report_2k.json`：五组数据的验收结果。

## 六 生成并运行 LoRA 微调配置

先用 0.5B（五亿参数）模型完成 Smoke Test（冒烟测试）：

```powershell
.\.venv-lora\Scripts\python.exe scripts\module4\03_prepare_llamafactory.py `
  --model Qwen/Qwen2.5-0.5B-Instruct `
  --template qwen `
  --n 2000 `
  --precision bf16
```

如果显卡不支持 BF16（Brain Floating Point 16，脑浮点 16 位），改用 `--precision fp16`，即 16 位浮点数。

生成完成后：

```powershell
call .venv-lora\Scripts\activate.bat
configs\module4\run_train.bat
configs\module4\run_merge.bat
```

脚本已使用独立的 `dataset_info.json`，不再要求你手工修改 LLaMA-Factory 安装目录。五组训练参数完全相同，检查点分别保存在 `experiments/module4/checkpoints`，合并后的模型保存在 `experiments/module4/merged_models`。

## 七 生成 OpenCompass 评测命令

建议 OpenCompass 使用独立虚拟环境，避免与 LLaMA-Factory 依赖冲突。完成模型合并后运行：

```powershell
python scripts\module4\04_make_eval_manifest.py `
  --base-model Qwen/Qwen2.5-0.5B-Instruct `
  --benchmarks ceval_gen cmmlu_gen `
  --workspace-dir D:\module4_opencompass
```

Windows 下 OpenCompass（开放式模型评测平台）的子进程可能错误解析中文路径。脚本会把五组合并模型映射到 `D:\module4_opencompass\models`，并把预测与评分结果写入 `D:\module4_opencompass\runs`。优先使用硬链接，因此通常不会额外占用五份完整模型空间；文件系统不支持硬链接时才会复制。

本地模型不能直接把 `D:\module4_opencompass\models\raw` 这类绝对路径当作模型简称。否则 OpenCompass 会把路径继续拼进任务输出名，造成日志、预测和评分文件落到模型目录或直接启动失败。本模块会自动生成 `module4-base-hf`、`module4-raw-hf`、`module4-rule-hf`、`module4-llm-only-hf`、`module4-datajuicer-hf` 和 `module4-ours-hf` 等安全简称。HF 是 Hugging Face（常用模型文件格式与工具生态）的缩写。

五组模型只微调模型参数，不修改分词规则，因此评测时统一复用基础模型的
Tokenizer（分词器），并设置 `use_fast=False` 使用兼容性更高的Python慢速分词器。
这可避开合并模型中 `tokenizer.json` 与独立评测环境的Rust快速分词器版本不一致所导致的
`ModelWrapper` 解析错误；只会让文本分词略慢，不会改变模型权重、预测逻辑或评分标准。

使用网页控制台时，只需保留“纯英文评测工作目录”的默认值，然后点击“生成评测配置”。每次重新合并模型后，都应再次生成评测配置，使英文模型映射同步更新。

升级模块4代码后也必须重新生成一次评测配置。旧日志中如果出现
`OpenICLEval[D:\module4_opencompass\models\raw.../ceval-...]`，说明仍在使用旧配置；
新配置的同一位置应显示 `OpenICLEval[module4-raw-hf/ceval-...]`。

先只检查配置：

```powershell
experiments\module4\evaluation\run_opencompass_dry_run.bat
```

确认没有错误后运行正式评测：

```powershell
experiments\module4\evaluation\run_opencompass.bat
```

评测 Base 与五组微调模型时使用相同的基准、推理长度、批量大小和模型加载参数。

## 八 汇总结果

网页控制台会自动从 `D:\module4_opencompass\runs` 中查找 Base、Raw、Rule、LLM-only、Data-Juicer、Ours
各自最新一次包含评分结果的运行，生成 `scores.csv` 和 `summary.csv`。因此通常不需要
手工整理CSV（逗号分隔值）文件。

如果OpenCompass自己的summary表已经生成，但成绩全部显示为 `-`，先检查对应运行目录
是否有 `predictions` 文件夹及JSON预测文件。存在预测答案时，网页中选择对应评测对象，
点击“仅重新评分”；该操作通过 `--reuse` 复用最新预测答案，只重新执行eval（评分）和
viz（结果展示）阶段，不重复进行耗时的模型推理。旧配置导致任务启动失败时没有有效预测
答案，不能只重新评分，必须重新生成配置并重新执行正式评测。完成后再点击“自动收集并汇总”。

如需使用外部分数表，仍可整理为：

```csv
model,benchmark,metric,seed,score
base,ceval,accuracy,42,50.2
raw,ceval,accuracy,42,51.0
rule,ceval,accuracy,42,52.1
llm_only,ceval,accuracy,42,52.8
datajuicer,ceval,accuracy,42,53.2
ours,ceval,accuracy,42,54.3
```

然后运行：

```powershell
python scripts\module4\05_compare_results.py `
  --input experiments\module4\results\scores.csv
```

若正式阶段使用三个随机种子，脚本会自动计算平均值和标准差。

## 九 错误样本回流

将逐题评测结果整理为 JSONL，字段可包含 `id`、`question`、`prediction`、`reference`、`correct`、`subject`：

```powershell
python scripts\module4\06_badcase_template.py `
  --input experiments\module4\results\ours_predictions.jsonl
```

输出文件交给：

- 任务二检查重复、乱码、无关内容等清洗规则；
- 任务三检查答案正确性、题答一致性、质量评价和学科覆盖。

## 十 正式实验公平性要求

- 五组样本数相同；
- 基础模型及具体版本相同；
- Epoch（训练轮数）、学习率、批量大小、梯度累积和 LoRA 参数相同；
- 使用相同且未进入训练集的测试集；
- 第一轮固定随机种子，正式阶段至少使用三个种子；
- 保留数据清单、训练配置、日志、检查点、评测 CSV 和错误样本；
- Ours 如果没有优于 Raw、Rule、LLM-only 或 Data-Juicer，也必须如实报告并分析原因。
