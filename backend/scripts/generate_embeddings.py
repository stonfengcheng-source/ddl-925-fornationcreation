#!/usr/bin/env python3
"""
存量数据 Embedding 生成脚本

为所有 embedding 为 NULL 的数据集和任务生成向量嵌入。
支持断点续传、批量处理和进度显示。

使用方法:
    cd backend
    python -m scripts.generate_embeddings
    python -m scripts.generate_embeddings --batch-size 50 --max-retries 3
"""
import os
import sys
import argparse
import logging
import json
from datetime import datetime
from typing import List, Optional, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm import declarative_base

from app.services.embedding import EmbeddingService
from app.models.dataset import Dataset
from app.models.task import Task
from app.core.database import DATABASE_URL

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# 断点续传状态文件
CHECKPOINT_FILE = ".embedding_checkpoint.json"


def load_checkpoint() -> dict:
    """加载断点状态"""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载断点文件失败: {e}")
    return {"datasets": {"last_id": None, "completed": False}, "tasks": {"last_id": None, "completed": False}}


def save_checkpoint(checkpoint: dict) -> None:
    """保存断点状态"""
    try:
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(checkpoint, f, indent=2)
    except Exception as e:
        logger.warning(f"保存断点文件失败: {e}")


def extract_dataset_text(dataset: Dataset) -> str:
    """从数据集中提取文本"""
    parts = []

    if dataset.name:
        parts.append(f"数据集名称: {dataset.name}")

    if dataset.description:
        parts.append(f"描述: {dataset.description}")

    if dataset.data_type:
        parts.append(f"数据类型: {dataset.data_type}")

    if dataset.tags:
        if isinstance(dataset.tags, list):
            tags_str = ", ".join(str(tag) for tag in dataset.tags)
            parts.append(f"标签: {tags_str}")
        elif isinstance(dataset.tags, str):
            parts.append(f"标签: {dataset.tags}")

    if dataset.columns_info:
        if isinstance(dataset.columns_info, list):
            cols_str = ", ".join(str(col) for col in dataset.columns_info[:10])
            parts.append(f"字段: {cols_str}")

    return "\n".join(parts) if parts else ""


def extract_task_text(task: Task) -> str:
    """从任务中提取文本"""
    parts = []

    if task.task_name:
        parts.append(f"任务名称: {task.task_name}")

    if task.task_category:
        parts.append(f"任务类别: {task.task_category}")

    if task.task_description:
        parts.append(f"任务描述: {task.task_description}")

    if task.task_tags:
        if isinstance(task.task_tags, list):
            tags_str = ", ".join(str(tag) for tag in task.task_tags)
            parts.append(f"任务标签: {tags_str}")
        elif isinstance(task.task_tags, str):
            parts.append(f"任务标签: {task.task_tags}")

    if task.data_formats:
        if isinstance(task.data_formats, list):
            formats_str = ", ".join(str(fmt) for fmt in task.data_formats)
            parts.append(f"数据格式: {formats_str}")
        elif isinstance(task.data_formats, str):
            parts.append(f"数据格式: {task.data_formats}")

    if task.model_type:
        parts.append(f"模型类型: {task.model_type}")

    return "\n".join(parts) if parts else ""


class EmbeddingGenerator:
    """Embedding 生成器"""

    def __init__(self, batch_size: int = 100, max_retries: int = 3):
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.stats = {
            "datasets": {"total": 0, "success": 0, "failed": 0, "skipped": 0},
            "tasks": {"total": 0, "success": 0, "failed": 0, "skipped": 0},
        }

        # 创建数据库连接
        self.engine = create_engine(DATABASE_URL, pool_pre_ping=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_db(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    def get_datasets_without_embedding(self, last_id: Optional[str] = None) -> List[Dataset]:
        """获取没有 embedding 的数据集"""
        db = self.get_db()
        try:
            query = db.query(Dataset).filter(Dataset.embedding.is_(None))
            if last_id:
                query = query.filter(Dataset.id > last_id)
            return query.order_by(Dataset.id).limit(self.batch_size).all()
        finally:
            db.close()

    def get_tasks_without_embedding(self, last_id: Optional[str] = None) -> List[Task]:
        """获取没有 embedding 的任务"""
        db = self.get_db()
        try:
            query = db.query(Task).filter(Task.embedding.is_(None))
            if last_id:
                query = query.filter(Task.id > last_id)
            return query.order_by(Task.id).limit(self.batch_size).all()
        finally:
            db.close()

    async def process_datasets(self, checkpoint: dict) -> None:
        """处理数据集"""
        if checkpoint["datasets"]["completed"]:
            logger.info("数据集 embedding 生成已完成，跳过")
            return

        logger.info("开始处理数据集...")
        last_id = checkpoint["datasets"].get("last_id")

        while True:
            datasets = self.get_datasets_without_embedding(last_id)
            if not datasets:
                break

            self.stats["datasets"]["total"] += len(datasets)

            # 提取文本
            texts = []
            valid_datasets = []
            for dataset in datasets:
                text = extract_dataset_text(dataset)
                if text:
                    texts.append(text)
                    valid_datasets.append(dataset)
                else:
                    self.stats["datasets"]["skipped"] += 1
                    logger.warning(f"数据集无文本内容，跳过: {dataset.id}")

            if not texts:
                last_id = datasets[-1].id
                checkpoint["datasets"]["last_id"] = last_id
                save_checkpoint(checkpoint)
                continue

            # 批量生成 embedding
            logger.info(f"正在生成 {len(texts)} 个数据集的 embedding...")
            embeddings = await EmbeddingService.embed_batch(
                texts, batch_size=self.batch_size, max_retries=self.max_retries
            )

            # 更新数据库
            db = self.get_db()
            try:
                for dataset, embedding in zip(valid_datasets, embeddings):
                    if embedding:
                        dataset.embedding = embedding
                        db.merge(dataset)
                        self.stats["datasets"]["success"] += 1
                    else:
                        self.stats["datasets"]["failed"] += 1
                        logger.error(f"数据集 embedding 生成失败: {dataset.id}")

                db.commit()
                logger.info(f"已更新 {len([e for e in embeddings if e])} 个数据集的 embedding")

            except Exception as e:
                db.rollback()
                logger.error(f"数据库更新失败: {e}")
                self.stats["datasets"]["failed"] += len(valid_datasets)
            finally:
                db.close()

            # 更新断点
            last_id = datasets[-1].id
            checkpoint["datasets"]["last_id"] = last_id
            save_checkpoint(checkpoint)

            logger.info(f"数据集进度: 成功 {self.stats['datasets']['success']}, "
                       f"失败 {self.stats['datasets']['failed']}, "
                       f"跳过 {self.stats['datasets']['skipped']}")

        checkpoint["datasets"]["completed"] = True
        save_checkpoint(checkpoint)
        logger.info("数据集处理完成")

    async def process_tasks(self, checkpoint: dict) -> None:
        """处理任务"""
        if checkpoint["tasks"]["completed"]:
            logger.info("任务 embedding 生成已完成，跳过")
            return

        logger.info("开始处理任务...")
        last_id = checkpoint["tasks"].get("last_id")

        while True:
            tasks = self.get_tasks_without_embedding(last_id)
            if not tasks:
                break

            self.stats["tasks"]["total"] += len(tasks)

            # 提取文本
            texts = []
            valid_tasks = []
            for task in tasks:
                text = extract_task_text(task)
                if text:
                    texts.append(text)
                    valid_tasks.append(task)
                else:
                    self.stats["tasks"]["skipped"] += 1
                    logger.warning(f"任务无文本内容，跳过: {task.id}")

            if not texts:
                last_id = tasks[-1].id
                checkpoint["tasks"]["last_id"] = last_id
                save_checkpoint(checkpoint)
                continue

            # 批量生成 embedding
            logger.info(f"正在生成 {len(texts)} 个任务的 embedding...")
            embeddings = await EmbeddingService.embed_batch(
                texts, batch_size=self.batch_size, max_retries=self.max_retries
            )

            # 更新数据库
            db = self.get_db()
            try:
                for task, embedding in zip(valid_tasks, embeddings):
                    if embedding:
                        task.embedding = embedding
                        db.merge(task)
                        self.stats["tasks"]["success"] += 1
                    else:
                        self.stats["tasks"]["failed"] += 1
                        logger.error(f"任务 embedding 生成失败: {task.id}")

                db.commit()
                logger.info(f"已更新 {len([e for e in embeddings if e])} 个任务的 embedding")

            except Exception as e:
                db.rollback()
                logger.error(f"数据库更新失败: {e}")
                self.stats["tasks"]["failed"] += len(valid_tasks)
            finally:
                db.close()

            # 更新断点
            last_id = tasks[-1].id
            checkpoint["tasks"]["last_id"] = last_id
            save_checkpoint(checkpoint)

            logger.info(f"任务进度: 成功 {self.stats['tasks']['success']}, "
                       f"失败 {self.stats['tasks']['failed']}, "
                       f"跳过 {self.stats['tasks']['skipped']}")

        checkpoint["tasks"]["completed"] = True
        save_checkpoint(checkpoint)
        logger.info("任务处理完成")

    def print_summary(self) -> None:
        """打印统计摘要"""
        print("\n" + "=" * 60)
        print("Embedding 生成统计")
        print("=" * 60)

        print("\n【数据集】")
        print(f"  总计处理: {self.stats['datasets']['total']}")
        print(f"  成功: {self.stats['datasets']['success']}")
        print(f"  失败: {self.stats['datasets']['failed']}")
        print(f"  跳过: {self.stats['datasets']['skipped']}")

        print("\n【任务】")
        print(f"  总计处理: {self.stats['tasks']['total']}")
        print(f"  成功: {self.stats['tasks']['success']}")
        print(f"  失败: {self.stats['tasks']['failed']}")
        print(f"  跳过: {self.stats['tasks']['skipped']}")

        total_success = self.stats['datasets']['success'] + self.stats['tasks']['success']
        total_failed = self.stats['datasets']['failed'] + self.stats['tasks']['failed']
        total = total_success + total_failed

        if total > 0:
            success_rate = (total_success / total) * 100
            print(f"\n总体成功率: {success_rate:.1f}%")

        print("=" * 60)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="为存量数据生成 Embedding 向量",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m scripts.generate_embeddings
  python -m scripts.generate_embeddings --batch-size 50
  python -m scripts.generate_embeddings --reset-checkpoint
        """
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="每批处理的数据量 (默认: 100)"
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="API 调用最大重试次数 (默认: 3)"
    )

    parser.add_argument(
        "--reset-checkpoint",
        action="store_true",
        help="重置断点，从头开始处理"
    )

    parser.add_argument(
        "--datasets-only",
        action="store_true",
        help="仅处理数据集"
    )

    parser.add_argument(
        "--tasks-only",
        action="store_true",
        help="仅处理任务"
    )

    args = parser.parse_args()

    # 检查配置
    provider = os.getenv("EMBEDDING_PROVIDER", "openai")
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        logger.error("错误: OPENAI_API_KEY 未设置")
        logger.error("请在 .env 文件中配置 OPENAI_API_KEY")
        sys.exit(1)

    # 加载或重置断点
    if args.reset_checkpoint:
        checkpoint = {"datasets": {"last_id": None, "completed": False},
                     "tasks": {"last_id": None, "completed": False}}
        save_checkpoint(checkpoint)
        logger.info("已重置断点")
    else:
        checkpoint = load_checkpoint()

    # 创建生成器
    generator = EmbeddingGenerator(
        batch_size=args.batch_size,
        max_retries=args.max_retries
    )

    start_time = datetime.now()

    try:
        # 处理数据集
        if not args.tasks_only:
            await generator.process_datasets(checkpoint)

        # 处理任务
        if not args.datasets_only:
            await generator.process_tasks(checkpoint)

    except KeyboardInterrupt:
        logger.info("\n用户中断，已保存断点，可重新运行继续")
        save_checkpoint(checkpoint)
        sys.exit(0)

    except Exception as e:
        logger.error(f"处理过程中出错: {e}")
        save_checkpoint(checkpoint)
        raise

    # 打印统计
    generator.print_summary()

    duration = datetime.now() - start_time
    logger.info(f"总耗时: {duration}")

    # 清理断点文件（如果全部完成）
    if checkpoint["datasets"]["completed"] and checkpoint["tasks"]["completed"]:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
            logger.info("已清理断点文件")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
