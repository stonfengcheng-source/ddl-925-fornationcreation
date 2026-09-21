"""
文本嵌入服务，支持多提供商 (OpenAI / DeepSeek / BGE)
"""
import os
import asyncio
import logging
from typing import List, Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class EmbeddingService:
    """文本嵌入服务，支持多提供商"""

    # OpenAI 配置默认值
    DEFAULT_OPENAI_MODEL = "text-embedding-3-small"
    OPENAI_API_BASE = "https://api.openai.com/v1"
    OPENAI_MAX_TOKENS = 8191
    MAX_BATCH_SIZE = 2048

    # DeepSeek 配置
    DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL = "deepseek-embedding"  # 输出 1024 维

    # 智谱 AI (Zhipu) 配置
    ZHIPU_API_BASE = "https://open.bigmodel.cn/api/paas/v4"
    ZHIPU_MODEL = "embedding-3"  # 输出 1024 维

    TARGET_DIMENSION = 1536  # 数据库目标维度

    @staticmethod
    def _get_config() -> Dict[str, Any]:
        """延迟读取配置"""
        return {
            "provider": os.getenv("EMBEDDING_PROVIDER", "openai").lower().strip(),
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "openai_model": os.getenv("OPENAI_EMBEDDING_MODEL", EmbeddingService.DEFAULT_OPENAI_MODEL),
            "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY"),
            "deepseek_model": os.getenv("DEEPSEEK_EMBEDDING_MODEL", EmbeddingService.DEEPSEEK_MODEL),
            "zhipu_api_key": os.getenv("ZHIPU_API_KEY"),
            "zhipu_model": os.getenv("ZHIPU_EMBEDDING_MODEL", EmbeddingService.ZHIPU_MODEL),
            "zhipu_api_base": os.getenv("ZHIPU_API_BASE", EmbeddingService.ZHIPU_API_BASE),
            "bge_api_key": os.getenv("BGE_API_KEY"),
            "bge_api_url": os.getenv("BGE_API_URL", "http://localhost:8080"),
        }

    @staticmethod
    def _preprocess_text(text: str, max_tokens: int = OPENAI_MAX_TOKENS) -> str:
        """
        预处理文本，截断至 max_tokens

        简单估算：1 token ≈ 4 个字符（中文）或 4/3 个单词（英文）
        这里使用保守估算：平均 3 字符/token
        """
        if not text:
            return ""

        # 保守估算最大字符数
        max_chars = max_tokens * 3

        if len(text) > max_chars:
            text = text[:max_chars]
            logger.warning(f"文本被截断至 {max_chars} 字符（约 {max_tokens} tokens）")

        return text.strip()

    @staticmethod
    async def _embed_with_openai(
        text: str,
        api_key: str,
        model: str,
        max_retries: int = 3
    ) -> Optional[List[float]]:
        """
        使用 OpenAI API 生成嵌入向量

        Args:
            text: 输入文本
            api_key: OpenAI API Key
            model: 模型名称
            max_retries: 最大重试次数

        Returns:
            1536 维向量，失败返回 None
        """
        url = f"{EmbeddingService.OPENAI_API_BASE}/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "input": text,
            "model": model
        }

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, headers=headers, json=payload)

                    if response.status_code == 429:  # Rate limit
                        wait_time = 2 ** attempt  # 指数退避: 1, 2, 4 秒
                        logger.warning(f"OpenAI API 限流，等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    if "data" in data and len(data["data"]) > 0:
                        embedding = data["data"][0].get("embedding")
                        if embedding and len(embedding) == 1536:
                            return embedding
                        else:
                            logger.error(f"返回的向量维度错误: {len(embedding) if embedding else 'None'}")
                            return None
                    else:
                        logger.error(f"OpenAI API 返回格式错误: {data}")
                        return None

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"OpenAI API 限流，等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"OpenAI API HTTP 错误: {e.response.status_code} - {e.response.text}")
                if attempt == max_retries - 1:
                    return None
            except httpx.RequestError as e:
                logger.error(f"OpenAI API 请求错误: {str(e)}")
                if attempt == max_retries - 1:
                    return None
            except Exception as e:
                logger.error(f"OpenAI API 未知错误: {str(e)}")
                if attempt == max_retries - 1:
                    return None

            await asyncio.sleep(0.5 * (attempt + 1))  # 短暂延迟后重试

        return None

    @staticmethod
    async def _embed_with_bge(
        text: str,
        api_url: str,
        api_key: Optional[str] = None,
        max_retries: int = 3
    ) -> Optional[List[float]]:
        """
        使用 BGE API 生成嵌入向量

        Args:
            text: 输入文本
            api_url: BGE API 地址
            api_key: BGE API Key（可选）
            max_retries: 最大重试次数

        Returns:
            1536 维向量，失败返回 None
        """
        url = f"{api_url.rstrip('/')}/embeddings"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "input": text,
            "model": "bge-large-zh-v1.5"  # 默认模型
        }

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()

                    if "data" in data and len(data["data"]) > 0:
                        embedding = data["data"][0].get("embedding")
                        if embedding:
                            return embedding
                        else:
                            logger.error("BGE API 返回的 embedding 为空")
                            return None
                    else:
                        logger.error(f"BGE API 返回格式错误: {data}")
                        return None

            except httpx.HTTPStatusError as e:
                logger.error(f"BGE API HTTP 错误: {e.response.status_code} - {e.response.text}")
                if attempt == max_retries - 1:
                    return None
            except httpx.RequestError as e:
                logger.error(f"BGE API 请求错误: {str(e)}")
                if attempt == max_retries - 1:
                    return None
            except Exception as e:
                logger.error(f"BGE API 未知错误: {str(e)}")
                if attempt == max_retries - 1:
                    return None

            await asyncio.sleep(0.5 * (attempt + 1))

        return None

    @staticmethod
    def _adapt_dimension(embedding: List[float], target_dim: int = 1536) -> List[float]:
        """
        调整向量维度以匹配数据库要求

        DeepSeek 输出 1024 维，需要填充到 1536 维
        策略：用零填充到目标维度
        """
        current_dim = len(embedding)
        if current_dim == target_dim:
            return embedding
        elif current_dim < target_dim:
            # 用零填充
            padding = [0.0] * (target_dim - current_dim)
            return embedding + padding
        else:
            # 截断
            return embedding[:target_dim]

    @staticmethod
    async def _embed_with_deepseek(
        text: str,
        api_key: str,
        model: str,
        max_retries: int = 3
    ) -> Optional[List[float]]:
        """
        使用 DeepSeek API 生成嵌入向量

        DeepSeek API 与 OpenAI 兼容，但输出 1024 维
        需要适配到 1536 维

        Args:
            text: 输入文本
            api_key: DeepSeek API Key
            model: 模型名称
            max_retries: 最大重试次数

        Returns:
            1536 维向量（1024 维原始 + 512 维零填充），失败返回 None
        """
        url = f"{EmbeddingService.DEEPSEEK_API_BASE}/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "input": text,
            "model": model
        }

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, headers=headers, json=payload)

                    if response.status_code == 429:  # Rate limit
                        wait_time = 2 ** attempt
                        logger.warning(f"DeepSeek API 限流，等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    if "data" in data and len(data["data"]) > 0:
                        embedding = data["data"][0].get("embedding")
                        if embedding:
                            # 适配维度：1024 -> 1536
                            adapted = EmbeddingService._adapt_dimension(
                                embedding, EmbeddingService.TARGET_DIMENSION
                            )
                            logger.debug(f"DeepSeek embedding 维度适配: {len(embedding)} -> {len(adapted)}")
                            return adapted
                        else:
                            logger.error("DeepSeek API 返回的 embedding 为空")
                            return None
                    else:
                        logger.error(f"DeepSeek API 返回格式错误: {data}")
                        return None

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"DeepSeek API 限流，等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"DeepSeek API HTTP 错误: {e.response.status_code} - {e.response.text}")
                if attempt == max_retries - 1:
                    return None
            except httpx.RequestError as e:
                logger.error(f"DeepSeek API 请求错误: {str(e)}")
                if attempt == max_retries - 1:
                    return None
            except Exception as e:
                logger.error(f"DeepSeek API 未知错误: {str(e)}")
                if attempt == max_retries - 1:
                    return None

            await asyncio.sleep(0.5 * (attempt + 1))

        return None

    @staticmethod
    async def embed_text(text: str, max_retries: int = 3) -> Optional[List[float]]:
        """
        单文本嵌入

        Args:
            text: 输入文本
            max_retries: 最大重试次数

        Returns:
            1536 维向量，失败返回 None
        """
        if not text or not text.strip():
            logger.warning("输入文本为空，返回 None")
            return None

        config = EmbeddingService._get_config()
        provider = config["provider"]

        # 预处理文本
        processed_text = EmbeddingService._preprocess_text(text)

        if provider == "openai":
            api_key = config["openai_api_key"]
            if not api_key:
                logger.error("OPENAI_API_KEY 未配置")
                return None

            model = config["openai_model"]
            return await EmbeddingService._embed_with_openai(
                processed_text, api_key, model, max_retries
            )

        elif provider == "deepseek":
            api_key = config["deepseek_api_key"]
            if not api_key:
                logger.error("DEEPSEEK_API_KEY 未配置")
                return None

            model = config["deepseek_model"]
            return await EmbeddingService._embed_with_deepseek(
                processed_text, api_key, model, max_retries
            )

        elif provider == "zhipu":
            api_key = config["zhipu_api_key"]
            if not api_key:
                logger.error("ZHIPU_API_KEY 未配置")
                return None

            model = config["zhipu_model"]
            api_base = config["zhipu_api_base"]
            return await EmbeddingService._embed_with_zhipu(
                processed_text, api_key, model, api_base, max_retries
            )

        elif provider == "bge":
            api_url = config["bge_api_url"]
            api_key = config["bge_api_key"]
            return await EmbeddingService._embed_with_bge(
                processed_text, api_url, api_key, max_retries
            )

        else:
            logger.error(f"不支持的 embedding provider: {provider}")
            return None

    @staticmethod
    async def embed_batch(
        texts: List[str],
        batch_size: int = 100,
        max_retries: int = 3
    ) -> List[List[float]]:
        """
        批量文本嵌入

        Args:
            texts: 输入文本列表
            batch_size: 每批处理数量（避免 API 限制）
            max_retries: 每文本最大重试次数

        Returns:
            向量列表，失败的位置为 None
        """
        if not texts:
            return []

        config = EmbeddingService._get_config()
        provider = config["provider"]

        # 预处理所有文本
        processed_texts = [
            EmbeddingService._preprocess_text(t) if t else ""
            for t in texts
        ]

        results: List[Optional[List[float]]] = [None] * len(texts)

        # 分批处理
        for i in range(0, len(processed_texts), batch_size):
            batch = processed_texts[i:i + batch_size]
            batch_indices = list(range(i, min(i + batch_size, len(processed_texts))))

            if provider == "openai":
                # OpenAI 支持真正的批量 API 调用
                batch_results = await EmbeddingService._embed_batch_openai(
                    batch, max_retries
                )
            elif provider == "zhipu":
                # 智谱 AI 与 OpenAI API 兼容
                batch_results = await EmbeddingService._embed_batch_zhipu(
                    batch, max_retries
                )
            elif provider == "deepseek":
                # DeepSeek 与 OpenAI API 兼容，复用批量逻辑
                batch_results = await EmbeddingService._embed_batch_deepseek(
                    batch, max_retries
                )
            elif provider == "bge":
                # BGE 逐个调用
                batch_results = await EmbeddingService._embed_batch_bge(
                    batch, max_retries
                )
            else:
                logger.error(f"不支持的 embedding provider: {provider}")
                batch_results = [None] * len(batch)

            # 保存结果
            for idx, result in zip(batch_indices, batch_results):
                results[idx] = result

            # 批次间短暂延迟，避免限流
            if i + batch_size < len(processed_texts):
                await asyncio.sleep(0.1)

        return results

    @staticmethod
    async def _embed_batch_openai(
        texts: List[str],
        max_retries: int = 3
    ) -> List[Optional[List[float]]]:
        """
        使用 OpenAI 批量嵌入 API
        """
        config = EmbeddingService._get_config()
        api_key = config["openai_api_key"]
        model = config["openai_model"]

        if not api_key:
            logger.error("OPENAI_API_KEY 未配置")
            return [None] * len(texts)

        # 过滤空文本
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            return [None] * len(texts)

        url = f"{EmbeddingService.OPENAI_API_BASE}/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "input": valid_texts,
            "model": model
        }

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(url, headers=headers, json=payload)

                    if response.status_code == 429:
                        wait_time = 2 ** attempt
                        logger.warning(f"OpenAI API 限流，等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    if "data" in data:
                        # 构建结果映射
                        results = [None] * len(texts)
                        for item in data["data"]:
                            idx_in_batch = item.get("index", 0)
                            original_idx = valid_indices[idx_in_batch]
                            embedding = item.get("embedding")
                            if embedding:
                                results[original_idx] = embedding
                        return results
                    else:
                        logger.error(f"OpenAI API 返回格式错误: {data}")
                        return [None] * len(texts)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"OpenAI API 限流，等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"OpenAI API HTTP 错误: {e.response.status_code}")
                return [None] * len(texts)
            except Exception as e:
                logger.error(f"OpenAI API 错误: {str(e)}")
                if attempt == max_retries - 1:
                    return [None] * len(texts)

            await asyncio.sleep(0.5 * (attempt + 1))

        return [None] * len(texts)

    @staticmethod
    async def _embed_with_zhipu(
        text: str,
        api_key: str,
        model: str,
        api_base: str,
        max_retries: int = 3
    ) -> Optional[List[float]]:
        """
        使用智谱 AI (Zhipu/GLM-4) API 生成嵌入向量

        智谱 AI API 与 OpenAI 兼容，但输出 1024 维
        需要适配到 1536 维

        Args:
            text: 输入文本
            api_key: 智谱 AI API Key
            model: 模型名称 (embedding-3 或 embedding-2)
            api_base: API 基础 URL
            max_retries: 最大重试次数

        Returns:
            1536 维向量（1024 维原始 + 512 维零填充），失败返回 None
        """
        url = f"{api_base.rstrip('/')}/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "input": text,
            "model": model
        }

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, headers=headers, json=payload)

                    if response.status_code == 429:  # Rate limit
                        wait_time = 2 ** attempt
                        logger.warning(f"Zhipu API 限流，等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    if "data" in data and len(data["data"]) > 0:
                        embedding = data["data"][0].get("embedding")
                        if embedding:
                            # 适配维度：1024 -> 1536
                            adapted = EmbeddingService._adapt_dimension(
                                embedding, EmbeddingService.TARGET_DIMENSION
                            )
                            logger.debug(f"Zhipu embedding 维度适配: {len(embedding)} -> {len(adapted)}")
                            return adapted
                        else:
                            logger.error("Zhipu API 返回的 embedding 为空")
                            return None
                    else:
                        logger.error(f"Zhipu API 返回格式错误: {data}")
                        return None

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Zhipu API 限流，等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"Zhipu API HTTP 错误: {e.response.status_code} - {e.response.text}")
                if attempt == max_retries - 1:
                    return None
            except httpx.RequestError as e:
                logger.error(f"Zhipu API 请求错误: {str(e)}")
                if attempt == max_retries - 1:
                    return None
            except Exception as e:
                logger.error(f"Zhipu API 未知错误: {str(e)}")
                if attempt == max_retries - 1:
                    return None

            await asyncio.sleep(0.5 * (attempt + 1))

        return None

    @staticmethod
    async def _embed_batch_zhipu(
        texts: List[str],
        max_retries: int = 3
    ) -> List[Optional[List[float]]]:
        """
        使用智谱 AI 批量嵌入 API

        智谱 AI API 与 OpenAI 兼容，复用逻辑但做维度适配
        """
        config = EmbeddingService._get_config()
        api_key = config["zhipu_api_key"]
        model = config["zhipu_model"]
        api_base = config["zhipu_api_base"]

        if not api_key:
            logger.error("ZHIPU_API_KEY 未配置")
            return [None] * len(texts)

        # 过滤空文本
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            return [None] * len(texts)

        url = f"{api_base.rstrip('/')}/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "input": valid_texts,
            "model": model
        }

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(url, headers=headers, json=payload)

                    if response.status_code == 429:
                        wait_time = 2 ** attempt
                        logger.warning(f"Zhipu API 限流，等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    if "data" in data:
                        # 构建结果映射
                        results = [None] * len(texts)
                        for item in data["data"]:
                            idx_in_batch = item.get("index", 0)
                            original_idx = valid_indices[idx_in_batch]
                            embedding = item.get("embedding")
                            if embedding:
                                # 适配维度
                                adapted = EmbeddingService._adapt_dimension(
                                    embedding, EmbeddingService.TARGET_DIMENSION
                                )
                                results[original_idx] = adapted
                        return results
                    else:
                        logger.error(f"Zhipu API 返回格式错误: {data}")
                        return [None] * len(texts)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Zhipu API 限流，等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"Zhipu API HTTP 错误: {e.response.status_code}")
                return [None] * len(texts)
            except Exception as e:
                logger.error(f"Zhipu API 错误: {str(e)}")
                if attempt == max_retries - 1:
                    return [None] * len(texts)

            await asyncio.sleep(0.5 * (attempt + 1))

        return [None] * len(texts)

    @staticmethod
    async def _embed_batch_deepseek(
        texts: List[str],
        max_retries: int = 3
    ) -> List[Optional[List[float]]]:
        """
        使用 DeepSeek 批量嵌入 API

        DeepSeek API 与 OpenAI 兼容，复用逻辑但做维度适配
        """
        config = EmbeddingService._get_config()
        api_key = config["deepseek_api_key"]
        model = config["deepseek_model"]

        if not api_key:
            logger.error("DEEPSEEK_API_KEY 未配置")
            return [None] * len(texts)

        # 过滤空文本
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            return [None] * len(texts)

        url = f"{EmbeddingService.DEEPSEEK_API_BASE}/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "input": valid_texts,
            "model": model
        }

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(url, headers=headers, json=payload)

                    if response.status_code == 429:
                        wait_time = 2 ** attempt
                        logger.warning(f"DeepSeek API 限流，等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    if "data" in data:
                        # 构建结果映射
                        results = [None] * len(texts)
                        for item in data["data"]:
                            idx_in_batch = item.get("index", 0)
                            original_idx = valid_indices[idx_in_batch]
                            embedding = item.get("embedding")
                            if embedding:
                                # 适配维度
                                adapted = EmbeddingService._adapt_dimension(
                                    embedding, EmbeddingService.TARGET_DIMENSION
                                )
                                results[original_idx] = adapted
                        return results
                    else:
                        logger.error(f"DeepSeek API 返回格式错误: {data}")
                        return [None] * len(texts)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"DeepSeek API 限流，等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"DeepSeek API HTTP 错误: {e.response.status_code}")
                return [None] * len(texts)
            except Exception as e:
                logger.error(f"DeepSeek API 错误: {str(e)}")
                if attempt == max_retries - 1:
                    return [None] * len(texts)

            await asyncio.sleep(0.5 * (attempt + 1))

        return [None] * len(texts)

    @staticmethod
    async def _embed_batch_bge(
        texts: List[str],
        max_retries: int = 3
    ) -> List[Optional[List[float]]]:
        """
        使用 BGE 逐个嵌入（并发）
        """
        config = EmbeddingService._get_config()
        api_url = config["bge_api_url"]
        api_key = config["bge_api_key"]

        # 并发调用
        tasks = [
            EmbeddingService._embed_with_bge(text, api_url, api_key, max_retries)
            for text in texts
        ]
        return await asyncio.gather(*tasks)
