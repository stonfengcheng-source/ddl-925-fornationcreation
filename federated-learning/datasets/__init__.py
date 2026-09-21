"""
数据集注册表
根据 model_type 字符串获取对应的数据集加载函数
所有数据集统一从 CSV 文件加载，符合隐私数据联邦流通的真实场景
"""

from datasets.breast_cancer import load_breast_cancer_partition
from datasets.diabetes import load_diabetes_partition
from datasets.heart_disease import load_heart_disease_partition
from datasets.credit_score import load_credit_score_partition
from datasets.adult_income import load_adult_income_partition
from datasets.bank_marketing import load_bank_marketing_partition


# 数据集注册表：model_type -> 加载函数
DATASET_REGISTRY = {
    "breast_cancer": load_breast_cancer_partition,
    "diabetes_mlp": load_diabetes_partition,
    "heart_disease": load_heart_disease_partition,
    "credit_score": load_credit_score_partition,
    "adult_income": load_adult_income_partition,
    "bank_marketing": load_bank_marketing_partition,
}


def get_dataset_loader(model_type: str):
    """根据 model_type 获取数据集加载函数"""
    if model_type not in DATASET_REGISTRY:
        raise ValueError(f"未知的模型类型: {model_type}，可选: {list(DATASET_REGISTRY.keys())}")
    return DATASET_REGISTRY[model_type]


def load_partition(model_type: str, node_id: int, num_nodes: int = 2, batch_size: int = 32):
    """
    统一加载数据分区接口

    返回: (trainloader, testloader, num_train, num_test)
    """
    loader_fn = get_dataset_loader(model_type)
    return loader_fn(node_id=node_id, num_nodes=num_nodes, batch_size=batch_size)
