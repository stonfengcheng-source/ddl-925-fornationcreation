# 联邦学习模块 (Flower)

基于 [Flower](https://flower.ai/) 框架的横向联邦学习实现，支持 **6 种隐私敏感表格数据集** 和 **差分隐私保护**。

## 项目结构

```
federated-learning/
├── server.py              # Flower 服务端（协调器），支持 FedAvg + 差分隐私
├── client.py              # Flower 客户端（NumPyClient 实现）
├── run_client.py          # 客户端启动脚本
├── train.py               # 训练和评估函数
├── simulation.py          # 单机模拟脚本（快速验证）
├── generate_csv_datasets.py  # CSV 数据集生成脚本
├── run_6sample_demo.py    # 6 种数据集 Demo 脚本
├── models/                # 模型定义（插件化注册表）
│   ├── __init__.py        #   MODEL_REGISTRY
│   ├── breast_cancer.py   #   乳腺癌诊断 MLP (30→64→32→2)
│   ├── diabetes.py        #   糖尿病预测 MLP (10→64→32→1)
│   ├── heart_disease.py   #   心脏病诊断 MLP (13→64→32→2)
│   ├── credit_score.py    #   信用评估 MLP (20→64→32→2)
│   ├── adult_income.py    #   收入预测 MLP (14→128→64→2)
│   └── bank_marketing.py  #   银行营销预测 MLP (16→128→64→2)
├── datasets/              # 数据加载与分区（插件化注册表）
│   ├── __init__.py        #   DATASET_REGISTRY
│   ├── breast_cancer.py   #   乳腺癌 CSV 加载器
│   ├── diabetes.py        #   糖尿病 CSV 加载器
│   ├── heart_disease.py   #   心脏病 CSV 加载器
│   ├── credit_score.py    #   信用评估 CSV 加载器
│   ├── adult_income.py    #   收入预测 CSV 加载器
│   └── bank_marketing.py  #   银行营销 CSV 加载器
├── sample_data/           # 样本 CSV 数据
│   ├── *.csv              #   6 个完整数据集
│   ├── node_a/            #   节点 A 拆分（60%）
│   └── node_b/            #   节点 B 拆分（40%）
├── requirements.txt       # Python 依赖
└── README.md              # 本文件
```

## 快速开始

### 1. 安装依赖

```bash
cd federated-learning
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. 生成样本数据（首次运行）

```bash
python generate_csv_datasets.py
```

### 3. 方式一：单机模拟（推荐先用这个验证）

```bash
python simulation.py
```

可调参数：

```bash
python simulation.py --rounds 20 --num-clients 3 --model-type heart_disease
```

### 4. 方式二：多终端真实运行

**终端1 — 启动服务端（协调器）：**
```bash
python server.py --rounds 10 --min-clients 2 --model-type breast_cancer
```

**终端2 — 启动节点A：**
```bash
python run_client.py --node-id 0 --server 127.0.0.1:8080 --model-type breast_cancer
```

**终端3 — 启动节点B：**
```bash
python run_client.py --node-id 1 --server 127.0.0.1:8080 --model-type breast_cancer
```

### 5. 启用差分隐私

```bash
python server.py --rounds 10 --min-clients 2 --model-type breast_cancer \
    --dp --dp-noise 1.0 --dp-clip 1.0
```

自适应裁剪模式：

```bash
python server.py --rounds 10 --min-clients 2 --model-type breast_cancer \
    --dp --dp-noise 1.0 --dp-clip 1.0 --dp-adaptive
```

## 支持的数据集

| 模型标识 | 中文名 | 来源 | 样本数 | 特征数 | 任务类型 |
|---------|--------|------|--------|--------|---------|
| `breast_cancer` | 乳腺癌诊断 | sklearn 内置 | 569 | 30 | 二分类 |
| `diabetes_mlp` | 糖尿病预测 | sklearn 内置 | 442 | 10 | 回归 |
| `heart_disease` | 心脏病诊断 | UCI Cleveland | 303 | 13 | 二分类 |
| `credit_score` | 信用评估 | UCI German Credit | 1,000 | 20 | 二分类 |
| `adult_income` | 收入预测 | UCI Adult Census | 5,000 | 14 | 二分类 |
| `bank_marketing` | 银行营销预测 | UCI Bank Marketing | 4,521 | 16 | 二分类 |

## 差分隐私

支持两种服务端差分隐私模式：

- **固定裁剪** (`DifferentialPrivacyServerSideFixedClipping`)：使用固定范数裁剪每个客户端的模型更新
- **自适应裁剪** (`DifferentialPrivacyServerSideAdaptiveClipping`)：根据训练过程动态调整裁剪范数

参数说明：
- `--dp-noise`：噪声倍数（越大隐私越强，精度越低）
- `--dp-clip`：裁剪范数（限制单个客户端更新的最大幅度）
- `--dp-adaptive`：启用自适应裁剪

## 预期效果

| 数据集 | 10 轮准确率（无 DP） | 10 轮准确率（DP ε=1.0） |
|--------|---------------------|------------------------|
| breast_cancer | 93%~97% | 88%~94% |
| heart_disease | 75%~85% | 70%~80% |
| credit_score | 70%~78% | 65%~75% |
| adult_income | 78%~84% | 73%~80% |
| bank_marketing | 70%~80% | 65%~75% |

*diabetes_mlp 为回归任务，使用 MSE 而非准确率评估。*
