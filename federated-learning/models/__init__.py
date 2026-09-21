"""
模型注册表
根据 model_type 字符串获取对应的模型类和默认配置
所有模型均为 MLP 全连接网络，面向隐私敏感的表格数据联邦学习场景
"""

from models.breast_cancer import BreastCancerNet
from models.diabetes_mlp import DiabetesMLP
from models.heart_disease import HeartDiseaseNet
from models.credit_score import CreditScoreNet
from models.adult_income import AdultIncomeNet
from models.bank_marketing import BankMarketingNet


# 模型注册表：model_type -> (模型类, 默认配置)
MODEL_REGISTRY = {
    "breast_cancer": {
        "class": BreastCancerNet,
        "name": "乳腺癌诊断模型",
        "description": "三层全连接网络 (30→64→32→2)，用于乳腺癌二分类",
        "task_type": "classification",
        "num_classes": 2,
        "default_config": {
            "input_dim": 30,
            "num_classes": 2,
            "learning_rate": 0.001,
            "batch_size": 32,
            "local_epochs": 3,
        },
    },
    "diabetes_mlp": {
        "class": DiabetesMLP,
        "name": "糖尿病预测模型",
        "description": "三层全连接网络 (10→64→32→1)，用于糖尿病指标回归预测",
        "task_type": "regression",
        "num_classes": 1,
        "default_config": {
            "input_dim": 10,
            "learning_rate": 0.001,
            "batch_size": 32,
            "local_epochs": 3,
        },
    },
    "heart_disease": {
        "class": HeartDiseaseNet,
        "name": "心脏病诊断模型",
        "description": "三层全连接网络 (13→64→32→2)，用于心脏病风险二分类",
        "task_type": "classification",
        "num_classes": 2,
        "default_config": {
            "input_dim": 13,
            "num_classes": 2,
            "learning_rate": 0.001,
            "batch_size": 32,
            "local_epochs": 3,
        },
    },
    "credit_score": {
        "class": CreditScoreNet,
        "name": "信用评估模型",
        "description": "三层全连接网络 (20→64→32→2)，用于银行客户信用风险二分类",
        "task_type": "classification",
        "num_classes": 2,
        "default_config": {
            "input_dim": 20,
            "num_classes": 2,
            "learning_rate": 0.001,
            "batch_size": 32,
            "local_epochs": 3,
        },
    },
    "adult_income": {
        "class": AdultIncomeNet,
        "name": "收入预测模型",
        "description": "三层全连接网络 (14→128→64→2)，用于人口收入水平二分类",
        "task_type": "classification",
        "num_classes": 2,
        "default_config": {
            "input_dim": 14,
            "num_classes": 2,
            "learning_rate": 0.001,
            "batch_size": 64,
            "local_epochs": 3,
        },
    },
    "bank_marketing": {
        "class": BankMarketingNet,
        "name": "银行营销预测模型",
        "description": "三层全连接网络 (16→128→64→2)，用于银行营销响应二分类",
        "task_type": "classification",
        "num_classes": 2,
        "default_config": {
            "input_dim": 16,
            "num_classes": 2,
            "learning_rate": 0.001,
            "batch_size": 64,
            "local_epochs": 3,
        },
    },
}


def get_model_class(model_type: str):
    """根据 model_type 获取模型类"""
    if model_type not in MODEL_REGISTRY:
        raise ValueError(f"未知的模型类型: {model_type}，可选: {list(MODEL_REGISTRY.keys())}")
    return MODEL_REGISTRY[model_type]["class"]


def get_model_config(model_type: str) -> dict:
    """获取模型默认配置"""
    if model_type not in MODEL_REGISTRY:
        raise ValueError(f"未知的模型类型: {model_type}")
    return MODEL_REGISTRY[model_type]


def list_models() -> list:
    """列出所有可用模型"""
    return [
        {
            "model_type": k,
            "name": v["name"],
            "description": v["description"],
            "task_type": v["task_type"],
        }
        for k, v in MODEL_REGISTRY.items()
    ]
