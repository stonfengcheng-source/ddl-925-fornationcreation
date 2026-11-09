> 历史快照：本文中的“没有真实输入文件”描述的是 2026-10-28 的状态。真实 HTTP 联调已于 2026-10-29 完成；浏览器人工操作仍未验收。当前结果以 `docs/real_data_200_report.md` 为准。

# 前端与后端集成报告

## 页面

新增路由 `/app/preproject-data`，导航名称为“预立项数据处理”。页面由后端 API 提供目录、数据源、任务状态、统计、质量指标、待复核元数据和下载文件；页面不写入演示统计。

页面操作包括：

- 提交官方 200 / 5,000 条采集任务并轮询状态。
- 上传 JSONL、JSON、Parquet；填写数据集 ID、来源链接、许可证、revision 和 split。
- 校验本地结构与文件 SHA-256。
- 配置格式清洗、近似重复开关/阈值、版本名称；隐私检测强制开启，近似重复只待人工复核。
- 创建/取消/重试任务，轮询状态和进度；查看统计、五维指标、准入原因与待审原因。
- 下载处理 JSONL、统计、质量报告、manifest、去重/脱敏报告和待审队列。原始数据不提供下载接口。

## API

前缀：`/api/preproject-data`。新增：

- `GET /catalog`
- `POST /sources/fetch`、`GET /sources/fetch/{fetch_id}`
- `GET /sources`、`POST /sources/upload`、`GET /sources/{source_id}`、`POST /sources/{source_id}/validate`
- `GET /tasks`、`POST /tasks`、`GET /tasks/{task_id}`、`POST /tasks/{task_id}/cancel`、`POST /tasks/{task_id}/retry`
- `GET /tasks/{task_id}/results`、`GET /tasks/{task_id}/files/{filename}`

API 复用现有登录用户解析，限 buyer/admin；存储目录按用户 ID 哈希分隔；任务下载只允许生成的安全文件白名单。单文件上传限制 100 MiB、每源 100,000 条；线程池最多 2 个任务，适配单进程小规模验证，不是分布式队列。

## 验证结果与边界（2026-10-28）

- 正在运行的 FastAPI `/health` 为 HTTP 200；模块四状态与预立项目录、数据源、任务接口均为 HTTP 200。通过 Vite `/api` 代理的同一组请求也均为 HTTP 200。
- 前端模块四、预立项页面、运行环境工具定向测试合计 22/22 通过；`npm run build` 通过。
- 桌面 API 基址已从 8765 改为 `VITE_PLATFORM_API_BASE_URL` 或 `http://127.0.0.1:8000/api`。Web 模式继续走 `/api` 代理。
- 预立项数据源与任务列表当前为空。没有真实输入文件，因此上传、校验、处理、取消/重试和下载未做写入型验收。
- 模块四状态显示训练解释器匹配，但 `torch`、`transformers`、`datasets`、`peft`、`llamafactory` 缺失且没有 `llamafactory-cli`；训练未就绪。
- 后端针对环境摘要的 pytest 在本机测试进程中无输出，尝试后已中止；不记为通过。运行服务的新状态接口已直接验证。
- 按用户隐私要求，没有控制 Edge 或进行浏览器视觉检查。真实数据版处理结果、实际统计和结果文件下载一致性仍未验收。
# 第七轮更新（2026-11-08）

隔离 HTTP 流程的真实 200 条数据处理和下载结果见 `data/preproject/api-v2-isolated/http_results.json`。任务、质量、版本、审核、下载由现有 API 提供；审核的确认保留、取消和失败重试以独立夹具验证。审核编辑并未完成全流程复检，其他审核操作和重启恢复尚未在本轮验证。前端组件通过定向测试，但未进行浏览器真实交互验收，完整需求尚未完成。

---

