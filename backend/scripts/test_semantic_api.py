#!/usr/bin/env python3
"""
测试语义推荐 API

用法:
    cd backend
    python -m scripts.test_semantic_api
"""
import os
import sys
import asyncio
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db
from app.services.semantic_matching import SemanticMatchingService


def get_token():
    """获取测试用的 JWT token"""
    # 这里简化处理，实际测试需要通过登录 API 获取
    # 或者使用已知的测试 token
    return None


async def test_semantic_matching_service():
    """直接测试语义匹配服务"""
    print("=" * 60)
    print("测试 SemanticMatchingService")
    print("=" * 60)

    db = next(get_db())

    try:
        # 测试 1: 为任务匹配数据集
        print("\n[测试 1] 为任务匹配数据集...")
        task_id = "e8cbbac7-1e0b-46a3-bbe0-8128a2301507"

        results = await SemanticMatchingService.find_matching_datasets_for_task(
            db=db,
            task_id=task_id,
            top_k=5,
            min_similarity=0.0
        )

        print(f"找到 {len(results)} 个匹配数据集")
        for i, item in enumerate(results, 1):
            print(f"\n[{i}] {item['dataset_name']}")
            print(f"    总分: {item['scores']['total']:.2%}")
            print(f"    语义: {item['scores']['semantic']:.2%}")
            print(f"    标签: {item['scores']['tag']:.2%}")
            print(f"    数据量: {item['scores']['quantity']:.2%}")

        # 测试 2: 为 provider 推荐任务
        print("\n[测试 2] 为 provider 推荐任务...")
        # 使用数据集的 owner_id
        provider_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

        results = await SemanticMatchingService.find_matching_tasks_for_provider(
            db=db,
            provider_id=provider_id,
            top_k=5,
            min_similarity=0.0
        )

        print(f"找到 {len(results)} 个推荐任务")
        for i, item in enumerate(results, 1):
            print(f"\n[{i}] {item['task_name']}")
            print(f"    总分: {item['scores']['total']:.2%}")
            print(f"    语义: {item['scores']['semantic']:.2%}")
            print(f"    标签: {item['scores']['tag']:.2%}")
            print(f"    数据量: {item['scores']['quantity']:.2%}")

    finally:
        db.close()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


async def test_api_endpoints():
    """测试 API 端点 (需要运行中的服务器)"""
    print("\n" + "=" * 60)
    print("测试 API 端点")
    print("=" * 60)

    base_url = "http://localhost:8000/api/v1"

    # 注意：需要有效的 JWT token
    headers = {
        # "Authorization": "Bearer YOUR_TOKEN_HERE"
    }

    async with httpx.AsyncClient() as client:
        # 测试语义推荐
        print("\n[测试] GET /training/recommended-semantic")
        try:
            response = await client.get(
                f"{base_url}/training/recommended-semantic",
                headers=headers,
                params={"top_k": 5}
            )
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                print(f"响应: {response.json()}")
            else:
                print(f"错误: {response.text}")
        except Exception as e:
            print(f"请求失败: {e}")
            print("提示: 请确保服务器已启动 (python -m uvicorn app.main:app)")


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="测试语义推荐 API")
    parser.add_argument(
        "--api",
        action="store_true",
        help="测试 API 端点（需要运行中的服务器）"
    )

    args = parser.parse_args()

    if args.api:
        await test_api_endpoints()
    else:
        await test_semantic_matching_service()


if __name__ == "__main__":
    asyncio.run(main())
