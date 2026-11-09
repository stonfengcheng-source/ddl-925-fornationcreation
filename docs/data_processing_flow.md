# 数据处理与复核流程

`data_pipeline` 读取 JSONL、JSON（包含 Dataset Viewer 的 rows 格式）及可选 Parquet，规范化多轮对话，按配置清洗，执行精确、归一化和 SimHash 近重复检测、规则脱敏与复检，计算五维指标并生成状态分流和文件。`processed.jsonl` 包含可解析的处理记录，`qualified.jsonl` 仅包含 keep 记录。动作与终态分离。近重复仅进入复核。

PII 引擎为工程规则而非 Presidio；类别标签是关键词启发式估计。无参考分布与无可验证过期证据时显示 N/A。工程筛查不等同专业内容审核或正式发布许可。

审核编辑先应用于规范化记录，再重新清洗、对全数据集去重、脱敏及质量计算，形成新的复核版本；编辑不会绕过 drop、quarantine 或仍存在的 review。确认保留仅解除可审核的 review，不覆盖隔离和删除。审核决定保存在后端用户目录中。
