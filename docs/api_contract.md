# 预立项 API 约定

前缀 `/api/preproject-data`；使用现有认证，操作角色为 buyer/admin。真实服务的 `/openapi.json` 为参数和响应结构的权威来源。

`GET /catalog`、`GET /sources`、`POST /sources/upload`、`POST /sources/{id}/validate`、`GET /sources/{id}/preview` 完成数据源管理。`POST /sources/demo-fixture` 仅在本机免密开发模式登记 TEST-ONLY 数据。`POST /tasks` 提交配置；`GET /tasks/{id}` 返回真实状态和日志；`POST /tasks/{id}/cancel` 和 `/retry` 控制任务。`GET /tasks/{id}/results` 返回统计、质量、准入及实际可下载文件。`GET /tasks/{id}/samples` 提供脱敏前后对照；`GET /tasks/{id}/review-items`、`POST /tasks/{id}/reviews` 和 `GET /tasks/{id}/reviews` 处理审核；`GET /versions` 和 `GET /version-comparison?left=...&right=...` 查询版本及样本差异。文件通过 `GET /tasks/{id}/files/{filename}` 下载；不存在或不在白名单的文件返回 404。发布候选需来源、许可和授权均核验，否则返回 409。

审核请求携带队列的 `expected_revision`，冲突返回 409；复检失败时记录为 pending，可调用 `POST /tasks/{id}/reviews/rebuild` 恢复。公开响应剔除服务器文件路径；处理结果中新生成的统计与清单使用便携路径。密码模式和非本地访问不开放测试夹具初始化。

对于 raw 版本，当前比较仅有样本 ID，无法从该接口可靠得出内容变化，返回 null 和原因。应用实际响应应以运行中的 OpenAPI 及接口为准。
# 第十轮接口补充

- `GET /api/preproject-data/sources/local-educhat/status` 检查项目内固定 EduChat 文件及清单；`POST /api/preproject-data/sources/local-educhat` 校验并为当前用户登记。不得通过参数指定任意服务器路径。
- `GET /api/module4/candidate-versions` 列出当前用户已完成处理、文件校验通过的候选版本；`POST /api/module4/prepare-candidate-config` 按版本生成用户隔离的训练输入和配置，不运行训练。
- `POST /api/module4/preflight` 返回模型、训练环境、评测配置及依赖的结构化检查；`POST /api/module4/run` 在训练或评测条件不足时返回 409，正式评测还要求匹配当前配置的试运行成功。清单通过 `make_eval_manifest` 操作生成，不代表评测已运行。

# 第十三轮轻量分类实验接口

`GET /api/baseline/environment` 检查独立解释器及实际 CPU fit；`GET /api/baseline/versions` 列出用户可见版本及显式分类标签兼容性；`POST /api/baseline/experiments` 接收 `version_id`、`seed`、`test_size`，仅对授权数据或内置合成分类数据创建真实训练任务。`GET /api/baseline/experiments` 和 `GET /api/baseline/experiments/{id}` 返回用户自己的历史、状态、真实指标及错误样本。`GET /api/baseline/experiments/{id}/files/{filename}` 仅允许下载预设的模型、配置、拆分、预测、错误样本、指标和报告。

