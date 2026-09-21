"""
语义匹配服务 - 基于向量相似度的智能推荐

提供任务-数据集之间的语义相似度计算，
支持混合评分策略（语义 + 标签 + 数据量）。
"""
import asyncio
import logging
import time
from typing import List, Optional, Dict, Any, Tuple
from functools import lru_cache
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.embedding import EmbeddingService
from app.models.task import Task
from app.models.dataset import Dataset

logger = logging.getLogger(__name__)

# 简单的 TTL 缓存实现
class SimpleCache:
    """带过期时间的内存缓存"""

    def __init__(self, ttl_seconds: int = 300):
        self._cache = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        value, expire_time = self._cache[key]
        if time.time() > expire_time:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: Any):
        expire_time = time.time() + self._ttl
        self._cache[key] = (value, expire_time)

    def clear(self):
        self._cache.clear()


class SemanticMatchingService:
    """语义匹配服务，基于向量相似度"""

    # 混合评分权重
    WEIGHTS = {
        "semantic": 0.5,  # 语义相似度
        "tag": 0.3,       # 标签匹配
        "quantity": 0.2   # 数据量匹配
    }

    # 缓存实例（5分钟过期）
    _embedding_cache = SimpleCache(ttl_seconds=300)
    _provider_avg_cache = SimpleCache(ttl_seconds=300)

    @staticmethod
    def _get_embedding_from_db(db: Session, table: str, id: str) -> Optional[List[float]]:
        """
        从数据库获取指定记录的 embedding（带缓存）

        Args:
            db: 数据库会话
            table: 表名 (tasks 或 datasets)
            id: 记录 ID

        Returns:
            embedding 向量或 None
        """
        cache_key = f"{table}:{id}"

        # 先检查缓存
        cached = SemanticMatchingService._embedding_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            result = db.execute(
                text(f"SELECT embedding FROM {table} WHERE id = :id"),
                {"id": id}
            ).fetchone()

            if not result or not result.embedding:
                return None

            embedding_raw = result.embedding

            # 处理不同类型的 embedding 返回格式
            if isinstance(embedding_raw, str):
                import ast
                embedding = ast.literal_eval(embedding_raw)
            elif isinstance(embedding_raw, list):
                embedding = embedding_raw
            else:
                embedding = list(embedding_raw)

            # 存入缓存
            SemanticMatchingService._embedding_cache.set(cache_key, embedding)
            return embedding

        except Exception as e:
            logger.error(f"获取 {table}.{id} 的 embedding 失败: {e}")
            return None

    @staticmethod
    def _calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        计算两个向量的余弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            余弦相似度 (-1 到 1)
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        # 计算点积
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # 计算模长
        norm1 = sum(x * x for x in vec1) ** 0.5
        norm2 = sum(x * x for x in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    @staticmethod
    def _calculate_tag_score(task_tags: List[str], dataset_tags: List[str]) -> float:
        """
        计算标签匹配分数

        Args:
            task_tags: 任务标签列表
            dataset_tags: 数据集标签列表

        Returns:
            标签匹配分数 (0-1)
        """
        if not task_tags or not dataset_tags:
            return 0.0

        task_tag_set = set(t.lower() for t in task_tags if t)
        dataset_tag_set = set(t.lower() for t in dataset_tags if t)

        if not task_tag_set or not dataset_tag_set:
            return 0.0

        overlap = task_tag_set & dataset_tag_set
        union = task_tag_set | dataset_tag_set

        if not union:
            return 0.0

        return len(overlap) / len(union)

    @staticmethod
    def _calculate_quantity_score(
        dataset_rows: int,
        min_required: int,
        max_required: Optional[int] = None
    ) -> float:
        """
        计算数据量匹配分数

        Args:
            dataset_rows: 数据集行数
            min_required: 任务要求的最小数据量
            max_required: 任务要求的最大数据量（可选）

        Returns:
            数据量匹配分数 (0-1)
        """
        if not dataset_rows or dataset_rows <= 0:
            return 0.0

        if not min_required or min_required <= 0:
            min_required = 100  # 默认值

        # 基础分：是否满足最小要求
        if dataset_rows < min_required:
            return dataset_rows / min_required * 0.5  # 最多 0.5

        # 满足最小要求后，考虑是否超出太多
        if max_required and dataset_rows > max_required:
            # 超出最大值，给予一定惩罚
            return max(0.8, 1.0 - (dataset_rows - max_required) / max_required * 0.2)

        # 在合理范围内
        return min(1.0, 0.7 + (dataset_rows - min_required) / min_required * 0.3)

    @staticmethod
    def calculate_match_score(
        task: Task,
        dataset: Dataset,
        semantic_similarity: float
    ) -> Dict[str, float]:
        """
        计算任务和数据集的综合匹配分数

        Args:
            task: 任务对象
            dataset: 数据集对象
            semantic_similarity: 语义相似度 (0-1)

        Returns:
            包含各维度分数和总分的字典
        """
        # 标签匹配分
        tag_score = SemanticMatchingService._calculate_tag_score(
            task.task_tags or [],
            dataset.tags or []
        )

        # 数据量匹配分
        quantity_score = SemanticMatchingService._calculate_quantity_score(
            dataset.row_count or 0,
            task.min_data_size or 1000
        )

        # 综合评分（加权）
        weights = SemanticMatchingService.WEIGHTS
        total_score = (
            semantic_similarity * weights["semantic"] +
            tag_score * weights["tag"] +
            quantity_score * weights["quantity"]
        )

        return {
            "total": round(total_score, 4),
            "semantic": round(semantic_similarity, 4),
            "tag": round(tag_score, 4),
            "quantity": round(quantity_score, 4)
        }

    @staticmethod
    async def find_matching_datasets_for_task(
        db: Session,
        task_id: str,
        top_k: int = 10,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        为指定任务匹配最相似的数据集（使用 pgvector 原生索引优化）

        Args:
            db: 数据库会话
            task_id: 任务 ID
            top_k: 返回结果数量
            min_similarity: 最小相似度阈值

        Returns:
            匹配的数据集列表（含评分详情）
        """
        # 1. 获取任务的 embedding
        task_embedding = SemanticMatchingService._get_embedding_from_db(
            db, "tasks", task_id
        )

        if not task_embedding:
            logger.warning(f"任务 {task_id} 没有 embedding，返回空结果")
            return []

        # 2. 获取任务详情
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return []

        # 3. 使用 pgvector 原生索引进行相似度搜索（数据库层计算）
        embedding_str = '[' + ','.join(str(x) for x in task_embedding) + ']'

        # 使用 HNSW 索引优化的 SQL 查询
        sql = f"""
        SELECT
            id,
            name,
            description,
            data_type,
            tags,
            row_count,
            owner_id,
            1 - (embedding <=> '{embedding_str}'::vector) AS semantic_sim
        FROM datasets
        WHERE embedding IS NOT NULL
          AND 1 - (embedding <=> '{embedding_str}'::vector) >= {min_similarity}
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT {top_k * 2}  -- 取更多结果用于后续综合评分过滤
        """

        result = db.execute(text(sql))
        candidates = result.fetchall()

        # 4. 对候选结果计算综合匹配分数
        results = []
        for row in candidates:
            # 获取完整数据集对象用于计算综合分数
            dataset = db.query(Dataset).filter(Dataset.id == row.id).first()
            if not dataset:
                continue

            # 转换语义相似度到 0-1 范围
            semantic_sim = (row.semantic_sim + 1) / 2 if row.semantic_sim < 0 else row.semantic_sim

            # 计算综合匹配分数
            scores = SemanticMatchingService.calculate_match_score(
                task, dataset, semantic_sim
            )

            results.append({
                "dataset_id": row.id,
                "dataset_name": row.name,
                "description": row.description,
                "data_type": row.data_type,
                "row_count": row.row_count,
                "owner_id": row.owner_id,
                "scores": scores
            })

        # 5. 按总分排序并返回 Top-K
        results.sort(key=lambda x: x["scores"]["total"], reverse=True)
        return results[:top_k]

    @staticmethod
    async def find_matching_tasks_for_provider(
        db: Session,
        provider_id: str,
        top_k: int = 10,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        为数据提供者（provider）推荐最匹配的任务

        基于 provider 的所有数据集的聚合 embedding，
        找到语义上最相关的任务。

        Args:
            db: 数据库会话
            provider_id: 提供者用户 ID
            top_k: 返回结果数量
            min_similarity: 最小相似度阈值

        Returns:
            匹配的任务列表（含评分详情）
        """
        cache_key = f"provider_avg:{provider_id}"

        # 1. 检查缓存
        cached_result = SemanticMatchingService._provider_avg_cache.get(cache_key)
        if cached_result:
            avg_embedding, datasets, total_rows = cached_result
            logger.debug(f"使用缓存的 provider {provider_id} 聚合 embedding")
        else:
            # 2. 获取 provider 的所有数据集
            datasets = db.query(Dataset).filter(
                Dataset.owner_id == provider_id,
                Dataset.embedding.isnot(None)
            ).all()

            if not datasets:
                logger.info(f"Provider {provider_id} 没有数据集或没有 embedding")
                return []

            # 3. 计算 provider 的聚合 embedding（取平均）
            provider_embeddings = []
            total_rows = 0
            for dataset in datasets:
                emb = SemanticMatchingService._get_embedding_from_db(
                    db, "datasets", dataset.id
                )
                if emb:
                    provider_embeddings.append(emb)
                    total_rows += dataset.row_count or 0

            if not provider_embeddings:
                return []

            # 计算平均向量
            dim = len(provider_embeddings[0])
            avg_embedding = [
                sum(e[i] for e in provider_embeddings) / len(provider_embeddings)
                for i in range(dim)
            ]

            # 存入缓存
            SemanticMatchingService._provider_avg_cache.set(
                cache_key, (avg_embedding, datasets, total_rows)
            )

        # 4. 使用 pgvector 原生索引搜索相似任务
        embedding_str = '[' + ','.join(str(x) for x in avg_embedding) + ']'

        sql = f"""
        SELECT
            id,
            task_name,
            task_description,
            task_category,
            task_tags,
            status,
            min_data_size,
            reward_pool,
            1 - (embedding <=> '{embedding_str}'::vector) AS semantic_sim
        FROM tasks
        WHERE embedding IS NOT NULL
          AND status IN ('pending', 'matching')
          AND 1 - (embedding <=> '{embedding_str}'::vector) >= {min_similarity}
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT {top_k * 2}
        """

        result = db.execute(text(sql))
        candidates = result.fetchall()

        # 5. 对候选结果计算综合匹配分数
        results = []
        for row in candidates:
            task = db.query(Task).filter(Task.id == row.id).first()
            if not task:
                continue

            # 转换语义相似度
            semantic_sim = (row.semantic_sim + 1) / 2 if row.semantic_sim < 0 else row.semantic_sim

            # 计算综合匹配分数
            scores = SemanticMatchingService.calculate_match_score(
                task, datasets[0], semantic_sim
            )

            # 使用缓存的 total_rows
            scores["quantity"] = SemanticMatchingService._calculate_quantity_score(
                total_rows, task.min_data_size or 1000
            )

            # 重新计算总分
            weights = SemanticMatchingService.WEIGHTS
            scores["total"] = round(
                semantic_sim * weights["semantic"] +
                scores["tag"] * weights["tag"] +
                scores["quantity"] * weights["quantity"],
                4
            )

            results.append({
                "task_id": row.id,
                "task_name": row.task_name,
                "description": row.task_description,
                "category": row.task_category,
                "reward_pool": row.reward_pool,
                "scores": scores
            })

        # 5. 按总分排序并返回 Top-K
        results.sort(key=lambda x: x["scores"]["total"], reverse=True)
        return results[:top_k]

    @staticmethod
    async def semantic_search_datasets(
        db: Session,
        query_text: str,
        top_k: int = 10,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        基于查询文本语义搜索数据集

        Args:
            db: 数据库会话
            query_text: 查询文本
            top_k: 返回结果数量
            min_similarity: 最小相似度阈值

        Returns:
            相似数据集列表
        """
        # 1. 生成查询文本的 embedding
        query_embedding = await EmbeddingService.embed_text(query_text)

        if not query_embedding:
            logger.error("无法生成查询文本的 embedding")
            return []

        # 2. 获取所有有 embedding 的数据集
        datasets = db.query(Dataset).filter(Dataset.embedding.isnot(None)).all()

        # 3. 计算相似度
        results = []
        for dataset in datasets:
            dataset_embedding = SemanticMatchingService._get_embedding_from_db(
                db, "datasets", dataset.id
            )

            if not dataset_embedding:
                continue

            semantic_sim = SemanticMatchingService._calculate_cosine_similarity(
                query_embedding, dataset_embedding
            )
            semantic_sim = (semantic_sim + 1) / 2

            if semantic_sim < min_similarity:
                continue

            results.append({
                "dataset_id": dataset.id,
                "dataset_name": dataset.name,
                "description": dataset.description,
                "similarity": round(semantic_sim, 4)
            })

        # 4. 排序并返回
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
