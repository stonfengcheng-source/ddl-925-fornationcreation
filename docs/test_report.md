# 数据处理闭环测试与集成验收报告

## 实际数据闭环

本轮使用 `data/preproject/incoming/200/educhat_raw_200.jsonl` 中的 200 条用户提供 Viewer 数据，而非合成夹具。

- CLI 端：解析 200，JSON 错误 0，保留 200，状态计数守恒 200/200，运行时间记录 0.672 秒；重复候选 0；PII 模式命中/脱敏/残留 0，残留扫描通过。
- FastAPI：实际 HTTP 上传 201；来源查询、样本预览、验证、统计/质量、版本和文件下载均 200；创建任务 202，最终状态 completed。服务重启后来源、任务和版本仍可查询。
- CLI/API 比较：样本数、样本 ID、输入文件 SHA、终态/清洗/去重/隐私计数与可测质量结果一致。来源 ID、subset ID 和来源分布标签不同；处理 JSONL 字节哈希不同。
- 发布候选准入：未核验来源返回 409。人工审核使用独立 `TEST-ONLY` fixture 验证修改/隔离、审计和新版本生成，不计入真实样本数据结果。
- 未执行真实 HTTP 取消和失败重试流程；端点已实现，运行竞态代码有保护，但不能记为真实业务验收通过。

## 自动化检查

- `& 'C:\Users\wh\.conda\envs\good-for-all\python.exe' -m pytest data_pipeline\tests -q`：13 passed。
- `npm test -- --run src/pages/PreprojectData/index.test.tsx`：2 passed。
- `npm run build`：通过。现有提示包括动态导入混用和约 2.75 MB 的大 chunk。
- `& 'C:\Users\wh\.conda\envs\good-for-all\python.exe' -m compileall -q backend\app\api\preproject_data.py backend\app\core\database.py data_pipeline`：通过。

## 未验收/限制

- 浏览器人工验收：未运行，遵守不访问 Edge/浏览器的隐私要求。组件测试和真实 HTTP 集成不能等同于浏览器端实际上传、操作、下载。
- 5,000 条真实数据处理：未执行，因为数据文件尚未提供/获取。
- 官方精确 revision 与许可证：未独立核验；参见真实数据 Manifest。
- Data-Juicer、Presidio：没有实际集成或运行。
- 后端真实数据取消/失败重试：未验收。
- 完整前端全量测试套件未运行；此次只运行了预立项页面定向测试和构建。

## 测试隔离记录

一次早期 API 测试中，自定义 SQLite URL 未被启用，导致一条测试数据资产写入默认测试数据库。已识别并只删除该测试资产行，修正数据库 URL 选择，之后所有 HTTP 验收使用隔离 SQLite 文件和独立数据目录，并确认数据资产保存在隔离库中。
# 第七轮验证（2026-11-08）

- 真实 CLI：200 输入、200 输出及 200 工程质量合格；复读 JSONL、ID 唯一、数量守恒、文件哈希、动作记录、脱敏残留，及相同配置重复运行记录和五维质量指标一致。参见 `data/preproject/processed/educhat-200-validated-v2/`。
- 真实 HTTP：隔离存储与 SQLite 中执行上传、验证、预览、任务、状态、质量和版本查询、九种文件下载以及缺失文件 404；独立夹具执行确认保留、取消、故障重试并检查终态。`data/preproject/api-v2-isolated/http_results.json` 为请求记录。编辑、隔离、驳回和重启恢复未做本轮 HTTP 验收。
- `python -m pytest data_pipeline/tests -q`：13 passed。
- 预立项页面 Vitest：2 passed；全量 Vitest：46 passed、2 failed（模块四的两个排序用例在并行运行时超过 5 秒），不能记为全量通过。
- 前端 `npm run build`：通过（包含 TypeScript 检查）；存在大 chunk 和动态导入警告。
- 后端测试先因默认解释器缺少 FastAPI/httpx 而未收集，随后项目环境运行未完成并中断，不能记为通过。
- 按要求未启动浏览器；真实页面交互、响应式布局及完整前后端端到端验收未完成。

---

