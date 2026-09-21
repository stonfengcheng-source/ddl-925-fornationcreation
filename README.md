<div align="center">

# 🚀 科研数据联邦流通平台

**Research Data Federated Circulation Platform**

*基于联邦学习的科研数据任务协作系统*

[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9+-green.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18.2+-61DAFB.svg)](https://reactjs.org/)
[![Status](https://img.shields.io/badge/Status-In%20Development-yellow.svg)]()

[项目文档](docs/) · [架构设计](docs/architecture/) · [开发进度](docs/progress/)

</div>

---

## 📖 项目背景

科研机构面临严峻的数据孤岛困境：**高质量科研数据难以跨机构流通**。核心矛盾在于：

- 🔴 **数据需求方**：需要罕见病例、基因数据等高质量科研数据训练模型，但数据分散在各医院/研究所
- 🔴 **数据持有方**：拥有宝贵数据但不敢共享，担心隐私泄露和利益受损
- 🔴 **现有平台**：通用数据交易平台场景太泛，无法解决科研数据的特殊痛点（质量验证、贡献衡量、收益分配）

### 💡 我们的解决方案

以**任务**为核心载体，实现"数据不出域，价值可流通"：

- **任务定义**：数据需求方发布科研任务（如"联合训练肺癌诊断模型，准确率≥85%，需要1000例含基因数据的病例"）
- **智能匹配**：平台基于用户画像和任务需求，精准匹配符合条件的数据提供方
- **联邦训练**：多方在本地数据上协同训练，只有模型参数在加密状态下传输
- **质量保障**：研究者用自然语言定义质量规则，系统自动生成验证代码，边缘实时验证+云端批量审核
- **公平分账**：根据数据量、质量、特征独特度等多维度计算贡献，自动分配收益

---

## ✨ 核心创新

### 🔐 1. 横向与纵向联邦学习统一框架

科研数据协作场景复杂，往往横向与纵向联邦同时存在：
- **横向联邦**：多家医院拥有相同的特征结构（年龄、血压、CT影像），但患者不同
- **纵向联邦**：医院与基因公司拥有同一批患者，但特征不同（临床数据 vs 基因测序）
- **混合场景**：五家医院横向协作，其中两家分别对接基因公司和影像中心，形成纵向关系

我们的创新是设计**统一框架**，自动识别参与方关系，动态调整训练策略：
- 横向模式：梯度平均聚合，注重数据量与分布多样性
- 纵向模式：隐私保护下的特征对齐，注重特征独特度
- 混合模式：统一调度，分层处理

### 📊 2. 高质量数据集智能构建

科研数据对质量要求极高，传统验证方式效率低、表达能力有限。

**自然语言→验证代码**：
- 研究者用自然语言描述规则："参与者年龄18-65岁，血压收缩压90-140，无心脏病史"
- 大模型（KIMI K2.5）自动生成Python验证函数
- 代码下发至边缘节点，实时拦截不合格数据

**分层验证机制**：

| 层级 | 验证内容 | 执行位置 | 目的 |
|------|----------|----------|------|
| **边缘验证** | 单条数据：格式、范围、逻辑一致性 | 边缘节点 | 快速反馈，避免白填 |
| **云端审核** | 批量数据：异常检测、分布偏离、时序异常 | 云端 | 发现统计学质量问题 |

**安全性**：使用 RestrictedPython 沙箱执行生成代码，禁止危险操作。

### ⚖️ 3. 动态权重收益分配算法

联邦学习的收益分配必须公平，但横向与纵向的衡量标准不同：

**分层计算模型**：
```
总贡献度 = α × 数据量贡献 + β × 数据质量贡献 + γ × 特征独特度贡献
```

**动态权重策略**：

| 联邦类型 | 数据量(α) | 质量(β) | 独特度(γ) | 说明 |
|----------|-----------|---------|-----------|------|
| 横向联邦 | 高 | 中 | 零 | 特征结构相同；考虑分布惩罚/罕见奖励 |
| 纵向联邦 | 低 | 中 | 高 | 样本可能重叠；独特度用VIF衡量 |

### 🎯 4. 供需智能匹配算法

**2026-02-27 重大更新：基于文本嵌入的语义匹配系统**

传统关键词匹配存在语义缺失问题。新系统使用向量嵌入实现真正的语义理解：

**核心特性**：
- **多提供商 Embedding**: 支持 OpenAI、智谱AI、BGE、DeepSeek
- **混合评分算法**: 语义相似度(50%) + 标签匹配(30%) + 数据量匹配(20%)
- **HNSW 索引优化**: O(log n) 向量相似度搜索
- **自动 Embedding 生成**: 数据集/任务创建时自动生成向量

**双视角匹配**：
- **Provider 视角**: 基于拥有的数据集，推荐语义相关的任务
- **Buyer 视角**: 基于发布的任务，匹配语义相关的数据集

**匹配分数可视化**：
- 环形图展示综合匹配度
- 三维度条形图展示：语义相似度、标签匹配度、数据量匹配度
- 颜色编码：🔴低(<40%) 🟠中(40-70%) 🟢高(>70%)

**技术栈**：pgvector + HNSW 索引 + TTL 缓存 + 异步 Embedding 生成

---

#### 旧版匹配流程（关键词/标签匹配）
1. 硬过滤：排除明显不符合条件的（如年龄不符）
2. 向量相似度：使用预训练模型（sentence-transformers）计算任务需求与用户画像的余弦相似度
3. 综合评分：结合历史质量、活跃度、响应速度
4. 精准推送：只向Top K用户推送任务

### 🛡️ 5. 差分隐私安全保护

实现成本低、理论成熟的隐私保护方案：
- **梯度加噪声**：边缘节点上传梯度前添加噪声（epsilon参数控制强度，通常1-10）
- **隐私预算**：设定总预算（如epsilon_total=10），每轮消耗一部分，用完即止
- **可视化**：前端展示各节点隐私预算剩余量

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                      用户交互层                           │
│   任务发布端    │    数据提供方端    │    管理后台        │
│    (React)     │      (React)      │     (React)       │
└─────────────────────────────────────────────────────────┘
                          ↓ REST API
┌─────────────────────────────────────────────────────────┐
│                     业务逻辑层                            │
│  任务匹配引擎  │  质量验证  │  收益分配  │  隐私预算管理   │
│              FastAPI 后端服务                            │
└─────────────────────────────────────────────────────────┘
                          ↓ gRPC
┌─────────────────────────────────────────────────────────┐
│                    联邦学习执行层                          │
│         统一联邦协调器（支持横向/纵向/混合）               │
│    节点A ←→ 参数聚合器 ←→ 节点B ←→ 节点C                │
│    （本地训练 + 差分隐私 + RestrictedPython沙箱）         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    数据存储层                             │
│   PostgreSQL   │     Redis      │    本地数据存储        │
└─────────────────────────────────────────────────────────┘
```

### 技术栈

| 类别          | 技术选型                           | 说明                            |
| ------------- | ---------------------------------- | ------------------------------- |
| **后端**      | Python 3.9+ / FastAPI              | 高性能异步框架，自动生成API文档 |
| **前端**      | React 18 / TypeScript / Ant Design | 企业级UI组件库                  |
| **联邦学习**  | 自研统一框架（TensorFlow/PyTorch） | 支持横向、纵向、混合模式        |
| **大模型**    | KIMI K2.5 API                      | 自然语言生成验证代码            |
| **沙箱**      | RestrictedPython                   | 安全执行生成的代码              |
| **数据库**    | PostgreSQL 15+                     | 关系型数据，支持JSON字段        |
| **缓存/队列** | Redis 7+                           | 高性能缓存和消息队列            |
| **容器化**    | Docker / Docker Compose            | 开发环境一致性                  |
| **可视化**    | ECharts                            | 数据可视化                      |

---

## 📂 项目结构

```
data-task-platform/
│
├── docs/                          # 📚 技术文档
│   ├── architecture/              #   系统架构、API规范、数据库设计
│   ├── modules/                   #   模块详细技术文档
│   ├── meeting-notes/             #   会议记录
│   ├── progress/                  #   每周进度报告
│   ├── models/                    #   技术方向、设计文档
│   └── demo/                      #   演示材料、答辩PPT
│
├── backend/                       # 🔧 后端服务
│   ├── app/
│   │   ├── api/                   #   REST API路由
│   │   ├── models/                #   数据库ORM模型
│   │   ├── services/              #   业务逻辑层
│   │   │   ├── quality_validator.py       # 质量验证（NL→代码）
│   │   │   ├── contribution_calculator.py # 动态权重收益分配
│   │   │   ├── task_matcher.py            # 向量相似度供需匹配
│   │   │   ├── sandbox_executor.py        # RestrictedPython沙箱
│   │   │   └── privacy_budget.py          # 差分隐私预算管理
│   │   └── utils/                 #   工具函数
│   ├── tests/                     #   单元测试
│   ├── requirements.txt           #   Python依赖
│   └── README.md
│
├── frontend/                      # 🎨 前端应用
│   ├── src/
│   │   ├── components/            #   可复用组件
│   │   │   ├── QualityValidator/  #   质量规则编辑、代码生成展示
│   │   │   ├── ContributionChart/ #   贡献度可视化
│   │   │   └── PrivacyBudget/     #   隐私预算展示
│   │   ├── pages/                 #   页面组件
│   │   │   ├── TaskPublish/       #   任务发布页
│   │   │   ├── TaskMatching/      #   任务匹配结果页
│   │   │   ├── ProviderDashboard/ #   数据提供方仪表盘
│   │   │   └── Admin/             #   管理后台
│   │   ├── services/              #   API调用封装
│   │   └── stores/                #   状态管理(Zustand)
│   ├── package.json
│   └── README.md
│
├── federated-learning/            # 🔐 联邦学习模块
│   ├── orchestrator/              #   统一协调器（支持横/纵向）
│   ├── horizontal/                #   横向联邦实现
│   ├── vertical/                  #   纵向联邦实现
│   ├── node-simulator/            #   本地节点模拟
│   ├── requirements.txt
│   └── README.md
│
├── scripts/                       # 🛠️ 工具脚本
│   ├── setup-env.sh               #   环境搭建脚本
│   ├── init-db.sql                #   数据库初始化SQL
│   └── deploy.sh                  #   部署脚本
│
├── .gitignore                     # Git忽略规则
├── docker-compose.yml             # Docker编排配置
└── README.md                      # 项目说明文档
```

---

## 🚀 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Git 2.30+

### 克隆仓库

```bash
git clone https://github.com/RollingTheRock/data-task-platform.git
cd data-task-platform
```

### 后端启动

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

后端服务运行在：http://localhost:8000

API文档自动生成：http://localhost:8000/docs

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

前端应用运行在：http://localhost:5173

### 数据库初始化

```bash
psql -U postgres -f scripts/init-db.sql
```

详细的开发环境搭建指南见：[docs/architecture/setup-guide.md](docs/architecture/setup-guide.md)

---

## 👥 团队分工

| 角色                        | GitHub                                               | 主要职责                     | 负责模块                       |
| --------------------------- | ---------------------------------------------------- | ---------------------------- | ------------------------------ |
| **项目负责人** | [@RollingTheRock](https://github.com/RollingTheRock) | 架构设计、项目管理 | 系统设计、进度把控 |
| **联邦学习工程师** | [@boyu91685-cloud](https://github.com/boyu91685-cloud) | 联邦学习框架、训练流程 | 横向/纵向联邦统一框架、模型聚合 |
| **联邦学习工程师** | [@悦](https://github.com/zykyd) | 联邦学习算法、节点协调 | 差分隐私、隐私预算管理 |
| **联邦学习工程师** | [@袁卓荣](https://github.com/袁卓荣) | 联邦学习框架开发 | 联邦学习模块、节点通信 |
| **后端工程师** | [@cheng.s](https://github.com/cheng.s) | API开发、数据库设计 | FastAPI服务、质量验证、收益分配 |
| **前端工程师** | [@L11Lsy](https://github.com/L11Lsy) | 用户界面、可视化 | React应用、任务发布与匹配展示 |

---

## 📊 开发进度

### 项目时间线（2026.01 - 2026.04）

```
Week 1-2    ████████░░░░░░░░░░░░  基础设施搭建
Week 3-4    ░░░░░░░░████████░░░░  核心功能开发
Week 5-6    ░░░░░░░░░░░░░░██████  算法实现与集成
Week 7-8    ░░░░░░░░░░░░░░░░░░██  系统测试与Demo打磨
Week 9-10   ░░░░░░░░░░░░░░░░░░░░  答辩准备
```

### 当前里程碑

- [x] **Week 1**: 项目启动、GitHub仓库搭建、架构设计
- [x] **Week 2**: 数据库设计、API框架搭建、技术方向确定
- [x] **Week 3-4**: 横向联邦基础流程、质量验证原型、任务匹配
- [x] **Week 5-6**: 差分隐私实现、多数据集支持、跨机联邦训练测试
- [ ] **Week 7-8**: 端到端测试、混合场景Demo、性能优化
- [ ] **Week 9-10**: Demo录制、技术白皮书、答辩演练

查看详细进度：[docs/progress/milestones.md](docs/progress/milestones.md)

---

## 📚 文档导航

### 架构设计
- [系统整体架构](docs/architecture/system-design.md)
- [API接口规范](docs/architecture/api-specification.md)
- [API开发指南](docs/architecture/api-development-guide.md)
- [数据库设计](docs/architecture/database-schema.md)
- [Git协作规范](docs/architecture/git-workflow.md)

### 模块文档
- [架构与核心算法](docs/modules/architecture-and-algorithms.md)
- [联邦学习模块](docs/modules/federated-learning.md)
- [后端API模块](docs/modules/backend-api.md)
- [前端应用模块](docs/modules/frontend.md)
- [语义匹配模块](docs/modules/semantic-matching.md)

### 版本文档
- [Demo v1.0 — MVP 第一版](docs/demo/version_1.0.md)
- [Demo v2.0 — 差分隐私 + 多数据集](docs/demo/version_2.0.md) ⭐ 新

### 技术方向
- [技术方向详细说明](docs/models/technical-direction.md)

### 进度跟踪
- [每周例会记录](docs/meeting-notes/)
- [每周进度报告](docs/progress/weekly-reports/)
- [问题与解决方案](docs/progress/issues-log.md)

---

## 🎯 核心功能演示

### 端到端流程

```
发布科研任务 → 智能匹配数据提供方 → 自然语言定义质量规则
                                            ↓
模型达标自动分账 ← 联邦学习训练（差分隐私保护） ← 边缘实时验证
```

### 1. 任务发布与匹配

**任务定义**：
```
任务：肺癌诊断模型联合训练
需求：1000例含基因数据的病例，年龄18-65岁
质量要求：参与者血压收缩压90-140，无心脏病史
目标准确率：≥85%
```

**智能匹配**：系统基于用户画像（专业领域、历史质量评分、活跃度）推荐Top 10匹配的数据提供方。

### 2. 质量规则生成

研究者输入自然语言规则：
```
"参与者年龄必须在18到65岁之间，血压收缩压90到140，
舒张压60到90，且不能有心脏病史"
```

系统自动生成验证代码并下发至边缘节点，实时拦截不合格数据。

### 3. 联邦训练与隐私保护

- 各节点本地训练，梯度加噪声后上传
- 云端聚合参数，更新全局模型
- 前端实时展示：训练Loss、各节点隐私预算消耗

### 4. 收益分配展示

```
收益分配报告
━━━━━━━━━━━━━━━━━━━━━━━━━━
总收益：10000元

参与方        数据量    质量评分    独特度    贡献度    收益
医院A         500例     95分        -        35%      3500元
医院B         300例     90分        -        25%      2500元
基因公司C     800特征   88分        高       40%      4000元
```

---

## 🔗 相关资源

- **项目看板**: [GitHub Projects](https://github.com/RollingTheRock/data-task-platform/projects)
- **Issue跟踪**: [GitHub Issues](https://github.com/RollingTheRock/data-task-platform/issues)
- **技术博客**: [开发日志](docs/blog/)
- **参考论文**: [学术资料](docs/references/)

---

## 🤝 贡献指南

我们欢迎团队成员积极贡献！请遵循以下流程：

1. **创建分支**: `git checkout -b feature/你的功能`
2. **开发功能**: 编写代码并添加测试
3. **提交代码**: `git commit -m "feat: 功能描述"`
4. **推送分支**: `git push origin feature/你的功能`
5. **创建PR**: 在GitHub上创建Pull Request
6. **代码审查**: 等待至少1人Review通过
7. **合并代码**: PR通过后合并到develop分支

详见：[Git协作规范](docs/architecture/git-workflow.md)

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。

---

## 📮 联系我们

- **项目负责人**: [王若如]
- **邮箱**: 2891887360@qq.com
- **GitHub**: [@RollingTheRock](https://github.com/RollingTheRock)

---

<div align="center">

**🌟 如果这个项目对你有帮助，请给我们一个Star！🌟**

Made with ❤️ by 科研数据联邦流通平台团队

*最后更新: 2026-03-01*

</div>

---

## 🔍 语义匹配模块使用指南

### 环境配置

**1. 配置 Embedding 提供商**（`.env` 文件）

```bash
# 选择提供商: openai / glm / bge
device EMBEDDING_PROVIDER=glm

# OpenAI 配置
export OPENAI_API_KEY=your_openai_key
export OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# 智谱AI 配置
export GLM_API_KEY=your_glm_key
export GLM_MODEL=embedding-3
```

**2. 启动 pgvector 数据库**

```bash
docker run -d --name postgres-pgvector \
  -e POSTGRES_PASSWORD=password \
  -p 5433:5432 pgvector/pgvector:pg16
```

**3. 运行存量数据补充脚本**

```bash
cd backend
venv/Scripts/python -m scripts.generate_embeddings
```

### 功能使用

#### Provider - 查看推荐任务

1. 登录 Provider 账号 (`test_provider` / `Test123456`)
2. 进入 **Dashboard** 首页
3. 查看 **"为您推荐的任务"** 区域
4. 观察语义匹配分数和可视化图表

**匹配原理**：
- 系统提取 Provider 所有数据集的向量平均值
- 计算与待匹配任务的向量相似度
- 结合标签重叠度和数据量计算综合评分

#### Buyer - 查看匹配的数据集

1. 登录 Buyer 账号 (`test_buyer` / `Test123456`)
2. 发布一个联邦学习任务
3. 进入任务详情页
4. 点击 **"匹配的数据集"** Tab
5. 查看 AI 推荐的数据集列表

**匹配原理**：
- 系统提取任务的向量嵌入
- 使用 HNSW 索引快速搜索相似数据集
- 返回 Top K 最匹配的数据集及分数详情

### API 接口

**获取推荐任务**（Provider）
```bash
GET /api/training/recommended-semantic?top_k=6&min_similarity=0.3
Authorization: Bearer {token}
```

**获取匹配的数据集**（Buyer）
```bash
GET /api/training/{task_id}/matching-datasets?top_k=10&min_similarity=0.3
Authorization: Bearer {token}
```

### 性能优化

- **HNSW 索引**: 向量搜索从 O(n) 优化到 O(log n)
- **TTL 缓存**: Embedding 和 Provider 向量均值缓存 300 秒
- **异步生成**: 数据集/任务创建时异步生成 embedding，不阻塞主流程
- **批量处理**: 支持批量嵌入，减少 API 调用次数

---

*语义匹配模块文档结束*
