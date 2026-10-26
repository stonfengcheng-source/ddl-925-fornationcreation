# 模块4主平台集成

## 已完成的接入

- 前端：`frontend/src/pages/Module4/index.tsx`，路由 `/app/module4`，复用现有布局与侧栏。
- 菜单：数据筛选与模型验证，买方和管理员可见。
- 请求：`frontend/src/services/api/module4.ts`，复用平台 Axios 与会话 Token。
- 后端：`backend/app/api/module4.py`，由 `backend/app/main.py` 注册。
- 任务：`backend/app/services/module4.py`，调用 `scripts/module4` 脚本。
- 独立网页服务器、独立 HTML 和启动批处理已移除。

## HTTP 接口

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/module4/status` | 当前任务、日志和产物状态 |
| POST | `/api/module4/run` | 提交白名单动作和配置 |
| POST | `/api/module4/stop` | 停止当前任务及其 Windows 子进程 |
| POST | `/api/module4/clear` | 空闲时清理日志 |
| GET | `/api/module4/results` | 读取真实 summary.csv |

所有接口复用 `get_current_user` 并校验买方或管理员角色。未知动作返回 400，已有任务运行或停止中时返回 409。没有可关闭整个平台后端的模块4接口。

## 任务与文件

命令通过参数数组执行，不使用 shell。工作目录固定为项目根目录；实验结果写入 `experiments/module4`，训练配置写入 `configs/module4`。训练 Python 可在页面指定，OpenCompass 使用独立评测环境。

同一进程只允许一个任务，页面每两秒读取状态和日志。关闭页面不会影响任务，平台后端关闭时停止任务。当前使用原有单进程 Uvicorn 方式；多进程部署需接入共享队列和状态存储。

实验进度的各项独立判断，不要求前置项目先变绿。对应任务必须成功，并在本次执行中新建或更新产物，旧文件和仅返回成功但未更新文件均不计完成。参数匹配当前配置；运行中、失败和停止不标绿，多模型阶段需要当前所有成员都完成。重新生成上游数据、训练配置或模型会撤销依赖项的记录；单纯检查不会清除其他已完成项。刷新网页保留当前后端记录，重启后端后不会仅凭历史文件恢复绿色。

评测模型与数据组分别判断。Raw 数据存在不表示 Raw 模型已完成合并；选择全部可用模型时始终包含 Base，只加入已有完整配置和权重的微调模型。明确选择尚未完成训练、合并的模型会返回前置步骤提示。

`eval_max_out_len` 为所有模型统一的单题输出上限，默认 512，网页允许 64 到 1024。协议 v3 按模式、输出长度和精度分离预测与配置目录；结果元数据记录输出长度和运行目录，接口只展示匹配当前配置的结果。改变上限后必须重新生成预测，“仅重新评分”不能修复已截断的答案。

## 验证

- 前端：在 frontend 执行 `npm run build` 和 `npm test`。
- API：在 backend 环境执行 `python -m pytest app/tests/api/endpoints/test_module4.py`。
- 脚本：在项目根目录使用平台环境执行 `python -m unittest discover -s scripts/module4/tests -v`。
