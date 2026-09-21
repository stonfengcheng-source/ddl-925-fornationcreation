#!/usr/bin/env python3
"""
语义相似度搜索测试脚本

测试 pgvector 的向量相似度搜索功能。
使用余弦相似度 (<=> 操作符) 计算语义相似性。

用法:
    cd backend
    python -m scripts.test_semantic_search "乳腺癌医学影像数据"
"""
import os
import sys
import asyncio
import argparse
from typing import List, Optional, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.services.embedding import EmbeddingService
from app.core.database import DATABASE_URL


def get_db():
    """获取数据库会话"""
    engine = create_engine(DATABASE_URL, pool_pre_ping=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


async def search_similar_datasets(
    query_text: str,
    top_k: int = 5,
    min_similarity: float = 0.0
) -> List[Dict[str, Any]]:
    """
    搜索语义相似的数据集

    Args:
        query_text: 查询文本
        top_k: 返回结果数量
        min_similarity: 最小相似度阈值 (0-1)

    Returns:
        相似数据集列表，包含相似度分数
    """
    db = get_db()
    try:
        # 1. 生成查询文本的 embedding
        print(f"生成查询文本的 embedding: '{query_text}'")
        query_embedding = await EmbeddingService.embed_text(query_text)

        if not query_embedding:
            print("错误: 无法生成查询 embedding")
            return []

        print(f"查询向量维度: {len(query_embedding)}")

        # 2. 使用 pgvector 进行余弦相似度搜索
        # <=> 操作符计算余弦距离，1 - 余弦距离 = 余弦相似度
        # 注意：在 SQL 中直接嵌入向量字符串（本地脚本，可控风险）

        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'

        sql = f"""
        SELECT
            id,
            name,
            description,
            data_type,
            tags,
            row_count,
            1 - (embedding <=> '{embedding_str}'::vector) AS similarity
        FROM datasets
        WHERE embedding IS NOT NULL
          AND 1 - (embedding <=> '{embedding_str}'::vector) >= {min_similarity}
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT {top_k}
        """

        result = db.execute(text(sql))

        datasets = []
        for row in result:
            datasets.append({
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "data_type": row.data_type,
                "tags": row.tags,
                "row_count": row.row_count,
                "similarity": round(row.similarity, 4)
            })

        return datasets

    finally:
        db.close()


async def search_similar_tasks(
    query_text: str,
    top_k: int = 5,
    min_similarity: float = 0.0
) -> List[Dict[str, Any]]:
    """
    搜索语义相似的任务

    Args:
        query_text: 查询文本
        top_k: 返回结果数量
        min_similarity: 最小相似度阈值 (0-1)

    Returns:
        相似任务列表，包含相似度分数
    """
    db = get_db()
    try:
        # 1. 生成查询文本的 embedding
        print(f"生成查询文本的 embedding: '{query_text}'")
        query_embedding = await EmbeddingService.embed_text(query_text)

        if not query_embedding:
            print("错误: 无法生成查询 embedding")
            return []

        # 2. 使用 pgvector 进行余弦相似度搜索
        embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'

        sql = f"""
        SELECT
            id,
            task_name,
            task_description,
            task_category,
            task_tags,
            status,
            1 - (embedding <=> '{embedding_str}'::vector) AS similarity
        FROM tasks
        WHERE embedding IS NOT NULL
          AND 1 - (embedding <=> '{embedding_str}'::vector) >= {min_similarity}
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT {top_k}
        """

        result = db.execute(text(sql))

        tasks = []
        for row in result:
            tasks.append({
                "id": row.id,
                "task_name": row.task_name,
                "description": row.task_description[:100] + "..." if row.task_description and len(row.task_description) > 100 else row.task_description,
                "category": row.task_category,
                "tags": row.task_tags,
                "status": row.status,
                "similarity": round(row.similarity, 4)
            })

        return tasks

    finally:
        db.close()


async def match_datasets_to_task(task_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    为指定任务匹配最相似的数据集

    Args:
        task_id: 任务 ID
        top_k: 返回结果数量

    Returns:
        匹配的数据集列表
    """
    db = get_db()
    try:
        # 1. 获取任务的 embedding
        result = db.execute(
            text("SELECT task_name, task_description, embedding FROM tasks WHERE id = :task_id"),
            {"task_id": task_id}
        ).fetchone()

        if not result or not result.embedding:
            print(f"错误: 任务 {task_id} 不存在或没有 embedding")
            return []

        task_name = result.task_name
        task_embedding_raw = result.embedding

        # 处理不同类型的 embedding 返回格式
        if isinstance(task_embedding_raw, str):
            # 如果是字符串 '[a,b,c]'，解析为列表
            import ast
            task_embedding = ast.literal_eval(task_embedding_raw)
        elif isinstance(task_embedding_raw, list):
            task_embedding = task_embedding_raw
        else:
            # 可能是 numpy array 或其他类型
            task_embedding = list(task_embedding_raw)

        print(f"任务: {task_name}")
        print(f"任务向量维度: {len(task_embedding)}")

        # 2. 搜索相似数据集
        embedding_str = '[' + ','.join(str(x) for x in task_embedding) + ']'

        sql = f"""
        SELECT
            id,
            name,
            description,
            data_type,
            tags,
            row_count,
            1 - (embedding <=> '{embedding_str}'::vector) AS similarity
        FROM datasets
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT {top_k}
        """

        result = db.execute(text(sql))

        datasets = []
        for row in result:
            datasets.append({
                "id": row.id,
                "name": row.name,
                "description": row.description[:100] + "..." if row.description and len(row.description) > 100 else row.description,
                "data_type": row.data_type,
                "tags": row.tags,
                "row_count": row.row_count,
                "similarity": round(row.similarity, 4)
            })

        return datasets

    finally:
        db.close()


def print_results(title: str, results: List[Dict[str, Any]]):
    """打印搜索结果"""
    print("\n" + "=" * 60)
    print(f"{title}")
    print("=" * 60)

    if not results:
        print("未找到匹配结果")
        return

    for i, item in enumerate(results, 1):
        print(f"\n[{i}] 相似度: {item['similarity']:.2%}")
        print(f"    ID: {item['id'][:8]}...")
        if 'name' in item:
            print(f"    名称: {item['name']}")
        if 'task_name' in item:
            print(f"    任务: {item['task_name']}")
        if 'description' in item and item['description']:
            print(f"    描述: {item['description'][:80]}")
        if 'data_type' in item:
            print(f"    类型: {item['data_type']}")
        if 'category' in item:
            print(f"    类别: {item['category']}")
        if 'tags' in item and item['tags']:
            print(f"    标签: {item['tags']}")


async def main():
    parser = argparse.ArgumentParser(
        description="测试语义相似度搜索",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m scripts.test_semantic_search "乳腺癌医学影像数据"
  python -m scripts.test_semantic_search "图像分类任务" --type tasks
  python -m scripts.test_semantic_search --match-task <task_id>
        """
    )

    parser.add_argument(
        "query",
        nargs="?",
        default="医疗数据",
        help="查询文本 (默认: 医疗数据)"
    )

    parser.add_argument(
        "--type",
        choices=["datasets", "tasks", "both"],
        default="both",
        help="搜索类型 (默认: both)"
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="返回结果数量 (默认: 5)"
    )

    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.0,
        help="最小相似度阈值 0-1 (默认: 0)"
    )

    parser.add_argument(
        "--match-task",
        type=str,
        help="指定任务ID，自动匹配数据集"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("语义相似度搜索测试")
    print("=" * 60)
    print(f"数据库: {DATABASE_URL}")

    if args.match_task:
        # 为指定任务匹配数据集
        print(f"\n为任务 {args.match_task} 匹配数据集...")
        datasets = await match_datasets_to_task(args.match_task, args.top_k)
        print_results(f"任务匹配的数据集 (Top {args.top_k})", datasets)

    else:
        # 基于查询文本搜索
        if args.type in ("datasets", "both"):
            datasets = await search_similar_datasets(
                args.query, args.top_k, args.min_similarity
            )
            print_results(f"数据集语义搜索: '{args.query}' (Top {args.top_k})", datasets)

        if args.type in ("tasks", "both"):
            tasks = await search_similar_tasks(
                args.query, args.top_k, args.min_similarity
            )
            print_results(f"任务语义搜索: '{args.query}' (Top {args.top_k})", tasks)

    print("\n" + "=" * 60)
    print("搜索完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
