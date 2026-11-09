# Python 轻量训练验收

实际流程：治理后的合成分类版本 → 明确选择该版本 → 独立 Python 进程加载标签 → 按类别分层划分 → 拟合 TF-IDF + Logistic Regression → 持久化模型、拆分、配置、预测、错误样本和报告。随机种子 42，测试集比例 0.25；模型训练前拒绝缺失标签、单一类别和重复文本，训练与测试样本 ID 不重叠。

本次实际运行：54 条样本，训练 40 条、测试 14 条；Accuracy 0.642857、Macro-F1 0.654040，错误样本 5 条。矩阵及类别见 `evidence/baseline_acceptance.json`；指标由测试集真实预测计算，并由验收脚本独立复算，下载后的模型重载并复现预测。**这是合成数据上的轻量监督分类基线，不是 SFT、LoRA 收益或 Proxy 排序结论。**

`scripts/init_baseline_env.ps1` 可创建独立虚拟环境。默认 `--system-site-packages` 复用已有基础环境依赖，不修改基础环境但共享读取其包；在目标环境尚不存在时，使用 `-InstallDependencies` 可创建不继承基础包的环境并安装 `configs/baseline-requirements.txt`。已有复用环境不会被自动删除或转换；如需另建完全独立环境，可在新目录创建虚拟环境并通过 `BASELINE_PYTHON` 指定其解释器。离线环境应事先准备与目标 Python 和系统兼容的依赖包，再使用 pip 的 `--no-index --find-links` 指定离线目录。环境检查会实际进行一个小型 CPU fit；不下载模型。

实验结果和模型保存在用户隔离的本地存储中，API 限制用户与可下载文件类型；模型文件为 joblib 格式，仅应加载可信来源。训练状态在服务重启后保留；重启中断的任务标记失败，不会伪造成功或自动续跑。
