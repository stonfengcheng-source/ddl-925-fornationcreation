# v6 端到端验收

独立空数据库的真实 HTTP 验收由 `scripts/baseline_http_acceptance.py` 执行。它验证初始化不创建任务，用户提交治理任务，带标签的合格版本进入训练，模型及预测由真实 fit 生成；独立复算指标并重新加载下载的模型，检查跨用户拒绝及服务重启后的实验记录。问答版本的无标签训练请求返回 409。

验收使用本机已准备的轻量 Python 虚拟环境和既有 scikit-learn 依赖，不需要 CUDA。详细运行事件、指标和哈希见 `evidence/baseline_acceptance.json`。真实 EduChat 非合成数据的上轮运行证据在 `evidence/functional_results.json`；本轮若再次验证，须以本轮脚本输出为准。

前端组件测试使用模拟 API，不能代替浏览器或真实 HTTP；本轮未进行浏览器实操、视觉验收、真实大模型训练或 OpenCompass 正式评测。
