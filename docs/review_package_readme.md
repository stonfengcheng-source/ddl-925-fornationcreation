# 独立检查与运行说明

第十一轮入口和资源准备见 `end_to_end_workflow.md`、`platform_resource_management.md` 和 `integration_test_report.md`。运行审查包内 `scripts/product_integration_check.py` 可检查合成示例（使用隔离数据库和本机端口），真实 EduChat 检查需要自行提供真实文件及清单。没有浏览器、模型训练或正式评测验收。

第十轮修复与验收范围、模型环境阻塞及真实 HTTP 证据见 `functional_fix_report.md` 和 `evidence/functional_results.json`。如本机具备对应的 EduChat 文件及清单，可在数据源页点击“登记本机已有 EduChat 数据”，再验证、选择和处理；否则上传有权使用的文件。处理后的合格候选版本可在模型验证的数据准备页选择，生成训练配置并检查环境。审查包不包含真实原始数据。未进行浏览器实操或模型训练、评测。

`frontend/` 是 React/Vite UI、路由、API 和组件测试；`backend/` 是 FastAPI、认证、数据源、任务和审核接口；`data_pipeline/` 是规范化、去重、脱敏、质量及 CLI；`configs/` 是规则；`scripts/` 包括演示脚本；`demo-datasets/` 是 TEST-ONLY 输入；`evidence/` 是路径脱敏的真实运行记录。六个页面入口见 `frontend_architecture.md`。未提供截图，因为没有浏览器验收。

安装 Python 依赖 `python -m pip install -r backend/requirements.txt`，在 `frontend` 执行 `npm ci`。Windows PowerShell 中于项目根目录运行 `./scripts/start_demo.ps1`，结束时运行 `./scripts/stop_demo.ps1`；可用 `-Python`、`-ApiPort`、`-WebPort` 指定解释器和端口。演示模式会创建独立数据目录并以本地免密账号运行，不适合公开部署。访问启动脚本打印的工作台地址，在数据源页点击“导入 TEST-ONLY 演示数据”，或者上传有权使用的真实数据；本包不自动导入真实数据。

首次进入前端时先在登录页输入 `admin`（本地演示无需密码），再进入“预立项数据处理”。数据源列表明确区分 TEST-ONLY 和用户数据。

CLI 示例：`python -m data_pipeline run --config configs/preproject_pipeline.json --input data/preproject/incoming/200/educhat_raw_200.jsonl --source-manifest data/preproject/incoming/200/educhat_manifest.json --out-dir data/preproject/processed/local-run`。运行前自行提供这两个文件；不得使用本包证据代替数据源。

测试命令：`python -m pytest data_pipeline/tests -q`；前端执行 `npm test`、`npm run build`。运行状态、约束和未完成项见 `real_data_test_report.md`、`frontend_test_report.md`、`known_issues.md`。页面和 API 只展示实际生成的结果，正式发布需独立核验。
