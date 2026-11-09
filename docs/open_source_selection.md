# 开源组件选型与验证记录（第二轮）

评估对象按当前代码的实际用途区分为“已接入”“候选/未接入”。评估与安装是两回事：本机缺少联网条件和可用 Python 环境，因此本轮没有批量安装数据处理依赖。

| 项目 | 地址 / 版本 | 许可证与环境 | 本轮用途和结论 | 实际验证 |
|---|---|---|---|---|
| Hugging Face Datasets | [GitHub](https://github.com/huggingface/datasets)，5.0.1 | Apache-2.0；官方说明 Python 3.10+；CPU 即可。Windows 安装/运行未在本机核验。 | **已接入为可选组件**：用于本地 Parquet 读取，以及可选的 revision 固定流式读取。EduChat 默认采样仍走官方 datasets-server 行接口，以按随机 offset 稀疏读取，避免从流式文件开头取前 5,000 条形成偏差。 | 本地无 `datasets` 包；采集器用 mock 适配测试通过。Parquet 实读、HF 网络读取未验证。 |
| Data-Juicer | [GitHub](https://github.com/datajuicer/data-juicer)，1.6.0 | Apache-2.0；Python `>=3.10,<4`；项目核心依赖较多，Windows 说明存在，但本机未核验。GPU 非基础文本算子必要条件。 | **候选，未接管现有算法**。拟承担文本过滤、文档级去重和 MinHash；须先验证算子输入输出、trace/sample_id 关联、过滤原因导出及中文阈值，再替换第一轮自定义近似去重。 | 未安装，未执行真实数据算子；不声称已集成。 |
| Presidio | [官方仓库](https://github.com/data-privacy-stack/presidio)，未锁定发行版 | MIT；Analyzer/Anonymizer 组件；基础规则不要求 GPU，中文模型/语言覆盖与 Windows 组合尚未验证。 | **候选，未接管脱敏**。中文手机号、身份证、邮箱和地址需要明确的中文 recognizer 与误检/漏检验证；Presidio 英文默认能力不能作为中文准确率保证。 | 未安装；未验证中文识别器、残留率或误报率。当前流水线保留第一轮规则作为工程初筛，不能用于安全保证。 |
| datasketch | [GitHub](https://github.com/ekzhu/datasketch)，2.0.0 | MIT；Python `>=3.9`；NumPy/SciPy 依赖；CPU 可运行。 | **暂不选用**。若 Data-Juicer 的 MinHash 能满足中文与追踪要求，就不再重复维护第二套 MinHash。若其追踪能力不足，再单独比较 datasketch。 | 未安装或运行。第一轮 SimHash 暂留为本地原型逻辑，近似重复只标记复核，不自动删除。 |

## 本轮依赖策略

- 新采集与文件格式接入优先通过官方 `datasets` API；远程默认采集器是 Hugging Face 官方 datasets-server 行接口，不抓取网页。
- `datasets` 是可选依赖；Parquet 导入缺少它时会明确报缺依赖。当前没有 `pyarrow` / `datasets` 可用于真实 Parquet 测试。
- 未将 Data-Juicer、Presidio、datasketch 一起安装。版本和许可证核对结果不是“组件运行通过”的替代证据。
- EduChat 数据集页面声明 CC BY-NC 4.0。组件自身许可证与数据集许可证独立；当前仅按本地非商业研究处理，未授予商业使用或再分发权。

## 官方资料

- [Hugging Face Datasets 仓库与发布](https://github.com/huggingface/datasets)
- [Data-Juicer 仓库与算子文档](https://github.com/datajuicer/data-juicer)
- [Presidio 仓库](https://github.com/data-privacy-stack/presidio)
- [datasketch 仓库](https://github.com/ekzhu/datasketch)
