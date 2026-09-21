"""
向量写入钩子 - 在数据集/任务创建或更新时自动生成 embedding
"""
import asyncio
import logging
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.embedding import EmbeddingService
from app.models.dataset import Dataset
from app.models.task import Task
from app.core.database import DATABASE_URL

logger = logging.getLogger(__name__)

# 为异步任务创建同步数据库会话
def _get_sync_db() -> Session:
    """创建同步数据库会话（用于异步任务）"""
    engine = create_engine(DATABASE_URL, pool_pre_ping=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def _extract_dataset_text(dataset: Dataset) -> str:
    """
    从数据集中提取用于 embedding 的文本

    Args:
        dataset: Dataset 模型实例

    Returns:
        合并后的文本
    """
    parts: List[str] = []

    # 名称
    if dataset.name:
        parts.append(f"数据集名称: {dataset.name}")

    # 描述
    if dataset.description:
        parts.append(f"描述: {dataset.description}")

    # 数据类型
    if dataset.data_type:
        parts.append(f"数据类型: {dataset.data_type}")

    # 标签
    if dataset.tags:
        if isinstance(dataset.tags, list):
            tags_str = ", ".join(str(tag) for tag in dataset.tags)
            parts.append(f"标签: {tags_str}")
        elif isinstance(dataset.tags, str):
            parts.append(f"标签: {dataset.tags}")

    # 列信息
    if dataset.columns_info:
        if isinstance(dataset.columns_info, list):
            cols_str = ", ".join(str(col) for col in dataset.columns_info[:10])  # 限制列数
            parts.append(f"字段: {cols_str}")

    return "\n".join(parts) if parts else ""


def _extract_task_text(task: Task) -> str:
    """
    从任务中提取用于 embedding 的文本

    Args:
        task: Task 模型实例

    Returns:
        合并后的文本
    """
    parts: List[str] = []

    # 任务名称
    if task.task_name:
        parts.append(f"任务名称: {task.task_name}")

    # 任务类别
    if task.task_category:
        parts.append(f"任务类别: {task.task_category}")

    # 任务描述
    if task.task_description:
        parts.append(f"任务描述: {task.task_description}")

    # 标签
    if task.task_tags:
        if isinstance(task.task_tags, list):
            tags_str = ", ".join(str(tag) for tag in task.task_tags)
            parts.append(f"任务标签: {tags_str}")
        elif isinstance(task.task_tags, str):
            parts.append(f"任务标签: {task.task_tags}")

    # 数据格式要求
    if task.data_formats:
        if isinstance(task.data_formats, list):
            formats_str = ", ".join(str(fmt) for fmt in task.data_formats)
            parts.append(f"数据格式: {formats_str}")
        elif isinstance(task.data_formats, str):
            parts.append(f"数据格式: {task.data_formats}")

    # 模型类型
    if task.model_type:
        parts.append(f"模型类型: {task.model_type}")

    return "\n".join(parts) if parts else ""


async def _generate_embedding_async(text: str) -> Optional[List[float]]:
    """
    异步生成 embedding

    Args:
        text: 输入文本

    Returns:
        向量或 None
    """
    try:
        return await EmbeddingService.embed_text(text)
    except Exception as e:
        logger.error(f"生成 embedding 失败: {str(e)}")
        return None


def _update_dataset_embedding_sync(dataset_id: str) -> bool:
    """
    同步更新数据集 embedding（在线程池中运行）

    Args:
        dataset_id: 数据集 ID

    Returns:
        是否成功
    """
    db = None
    try:
        db = _get_sync_db()

        # 获取数据集
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            logger.warning(f"数据集不存在: {dataset_id}")
            return False

        # 提取文本
        text = _extract_dataset_text(dataset)
        if not text:
            logger.warning(f"数据集没有可嵌入的文本: {dataset_id}")
            return False

        # 生成 embedding（在新事件循环中运行异步代码）
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        embedding = loop.run_until_complete(_generate_embedding_async(text))

        if embedding is None:
            logger.error(f"生成数据集 embedding 失败: {dataset_id}")
            return False

        # 更新数据库
        dataset.embedding = embedding
        db.commit()
        logger.info(f"数据集 embedding 生成成功: {dataset_id}")
        return True

    except Exception as e:
        logger.error(f"更新数据集 embedding 失败: {dataset_id}, 错误: {str(e)}")
        if db:
            db.rollback()
        return False
    finally:
        if db:
            db.close()


def _update_task_embedding_sync(task_id: str) -> bool:
    """
    同步更新任务 embedding（在线程池中运行）

    Args:
        task_id: 任务 ID

    Returns:
        是否成功
    """
    db = None
    try:
        db = _get_sync_db()

        # 获取任务
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"任务不存在: {task_id}")
            return False

        # 提取文本
        text = _extract_task_text(task)
        if not text:
            logger.warning(f"任务没有可嵌入的文本: {task_id}")
            return False

        # 生成 embedding
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        embedding = loop.run_until_complete(_generate_embedding_async(text))

        if embedding is None:
            logger.error(f"生成任务 embedding 失败: {task_id}")
            return False

        # 更新数据库
        task.embedding = embedding
        db.commit()
        logger.info(f"任务 embedding 生成成功: {task_id}")
        return True

    except Exception as e:
        logger.error(f"更新任务 embedding 失败: {task_id}, 错误: {str(e)}")
        if db:
            db.rollback()
        return False
    finally:
        if db:
            db.close()


async def generate_dataset_embedding(dataset_id: str) -> bool:
    """
    为数据集生成 embedding（异步任务入口）

    在后台异步执行，不影响主流程

    Args:
        dataset_id: 数据集 ID

    Returns:
        是否成功启动任务（实际结果通过日志查看）
    """
    try:
        # 在线程池中执行同步数据库操作
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,  # 默认执行器
            _update_dataset_embedding_sync,
            dataset_id
        )
        return result
    except Exception as e:
        logger.error(f"启动数据集 embedding 任务失败: {dataset_id}, 错误: {str(e)}")
        return False


async def generate_task_embedding(task_id: str) -> bool:
    """
    为任务生成 embedding（异步任务入口）

    在后台异步执行，不影响主流程

    Args:
        task_id: 任务 ID

    Returns:
        是否成功启动任务（实际结果通过日志查看）
    """
    try:
        # 在线程池中执行同步数据库操作
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,  # 默认执行器
            _update_task_embedding_sync,
            task_id
        )
        return result
    except Exception as e:
        logger.error(f"启动任务 embedding 任务失败: {task_id}, 错误: {str(e)}")
        return False


def schedule_dataset_embedding(dataset_id: str) -> None:
    """
    调度数据集 embedding 生成任务

    使用 asyncio.create_task() 在后台执行

    Args:
        dataset_id: 数据集 ID
    """
    try:
        # 创建后台任务
        asyncio.create_task(generate_dataset_embedding(dataset_id))
        logger.debug(f"已调度数据集 embedding 任务: {dataset_id}")
    except RuntimeError:
        # 如果没有事件循环，记录日志
        logger.warning(f"无法创建后台任务（无事件循环），跳过 embedding 生成: {dataset_id}")
    except Exception as e:
        logger.error(f"调度数据集 embedding 任务失败: {dataset_id}, 错误: {str(e)}")


def schedule_task_embedding(task_id: str) -> None:
    """
    调度任务 embedding 生成任务

    使用 asyncio.create_task() 在后台执行

    Args:
        task_id: 任务 ID
    """
    try:
        # 创建后台任务
        asyncio.create_task(generate_task_embedding(task_id))
        logger.debug(f"已调度任务 embedding 任务: {task_id}")
    except RuntimeError:
        # 如果没有事件循环，记录日志
        logger.warning(f"无法创建后台任务（无事件循环），跳过 embedding 生成: {task_id}")
    except Exception as e:
        logger.error(f"调度任务 embedding 任务失败: {task_id}, 错误: {str(e)}")
