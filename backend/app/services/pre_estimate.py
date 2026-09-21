"""
训练前数据价值预评估服务
提供基于数据特征的贡献度预估算法
"""

from dataclasses import dataclass
from typing import List
import math


@dataclass
class ProviderData:
    """Provider数据输入"""
    provider_id: str
    provider_name: str
    data_volume: int
    quality_score: float


@dataclass
class ProviderEstimate:
    """Provider预估结果输出"""
    provider_id: str
    provider_name: str
    data_volume: int
    quality_score: float
    diversity_score: float
    estimated_ratio: float
    estimated_amount: float


def estimate_contributions(
    providers: List[ProviderData],
    reward_pool: float = 0.0
) -> List[ProviderEstimate]:
    """
    计算各Provider的预估贡献度

    算法:
    1. 多样性评分 = log(data_volume + 1) / log(max_volume + 1)
       - 使用对数函数降低大数据量的边际效益
       - 鼓励数据多样性而非单纯追求大数据量
    2. 原始贡献度 = (1/3) * (data_volume / total_volume)
                    + (1/3) * quality_score
                    + (1/3) * diversity_score
       - 综合考虑数据量、质量、多样性三个维度
    3. 归一化: estimated_ratio = raw_i / sum(all raw)
       - 确保所有比例之和为1

    Args:
        providers: Provider数据列表
        reward_pool: 奖励池金额，用于计算预估收益

    Returns:
        每个Provider的预估贡献度结果
    """
    if not providers:
        return []

    # 计算总数据量
    total_volume = sum(p.data_volume for p in providers)

    # 计算最大数据量（用于多样性评分）
    max_volume = max(p.data_volume for p in providers) if providers else 0

    # 避免除零
    if total_volume == 0 or max_volume == 0:
        # 如果数据量都为0，则只根据质量评分分配
        total_quality = sum(p.quality_score for p in providers)
        if total_quality == 0:
            # 所有评分都为0，平均分配
            equal_ratio = 1.0 / len(providers) if providers else 0
            return [
                ProviderEstimate(
                    provider_id=p.provider_id,
                    provider_name=p.provider_name,
                    data_volume=p.data_volume,
                    quality_score=p.quality_score,
                    diversity_score=0.0,
                    estimated_ratio=equal_ratio,
                    estimated_amount=reward_pool * equal_ratio
                )
                for p in providers
            ]
        else:
            # 按质量评分比例分配
            return [
                ProviderEstimate(
                    provider_id=p.provider_id,
                    provider_name=p.provider_name,
                    data_volume=p.data_volume,
                    quality_score=p.quality_score,
                    diversity_score=0.0,
                    estimated_ratio=p.quality_score / total_quality,
                    estimated_amount=reward_pool * p.quality_score / total_quality
                )
                for p in providers
            ]

    # 计算每个Provider的原始贡献度
    raw_contributions = []
    for p in providers:
        # 多样性评分：对数归一化
        diversity_score = math.log(p.data_volume + 1) / math.log(max_volume + 1)

        # 数据量占比（归一化到0-1）
        volume_ratio = p.data_volume / total_volume

        # 原始贡献度：三个维度等权重
        raw_contribution = (
            (1/3) * volume_ratio +
            (1/3) * p.quality_score +
            (1/3) * diversity_score
        )

        raw_contributions.append({
            'provider': p,
            'diversity_score': diversity_score,
            'raw_contribution': raw_contribution
        })

    # 计算原始贡献度总和
    total_raw = sum(rc['raw_contribution'] for rc in raw_contributions)

    # 归一化并生成结果
    results = []
    for rc in raw_contributions:
        provider = rc['provider']
        estimated_ratio = rc['raw_contribution'] / total_raw if total_raw > 0 else 0

        results.append(ProviderEstimate(
            provider_id=provider.provider_id,
            provider_name=provider.provider_name,
            data_volume=provider.data_volume,
            quality_score=provider.quality_score,
            diversity_score=rc['diversity_score'],
            estimated_ratio=estimated_ratio,
            estimated_amount=reward_pool * estimated_ratio
        ))

    # 按预估贡献度降序排序
    results.sort(key=lambda x: x.estimated_ratio, reverse=True)

    return results
