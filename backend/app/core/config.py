"""
配置管理 - 集中管理 Embedding 相关配置
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


@dataclass
class EmbeddingConfig:
    """Embedding 配置类"""

    # Provider 设置 (openai/deepseek/bge)
    provider: str = "openai"

    # OpenAI 配置
    openai_api_key: Optional[str] = None
    openai_model: str = "text-embedding-3-small"

    # DeepSeek 配置 (输出 1024 维，自动适配到 1536 维)
    deepseek_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-embedding"

    # 智谱 AI (Zhipu/GLM-4) 配置 (输出 1024 维，自动适配到 1536 维)
    zhipu_api_key: Optional[str] = None
    zhipu_model: str = "embedding-3"
    zhipu_api_base: str = "https://open.bigmodel.cn/api/paas/v4"

    # BGE 配置
    bge_api_key: Optional[str] = None
    bge_api_url: str = "http://localhost:8080"

    # 向量维度
    embedding_dimension: int = 1536

    # 批处理配置
    batch_size: int = 100

    # 重试配置
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "EmbeddingConfig":
        """从环境变量加载配置"""
        return cls(
            provider=os.getenv("EMBEDDING_PROVIDER", "openai").lower().strip(),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
            deepseek_model=os.getenv("DEEPSEEK_EMBEDDING_MODEL", "deepseek-embedding"),
            zhipu_api_key=os.getenv("ZHIPU_API_KEY"),
            zhipu_model=os.getenv("ZHIPU_EMBEDDING_MODEL", "embedding-3"),
            zhipu_api_base=os.getenv("ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4"),
            bge_api_key=os.getenv("BGE_API_KEY"),
            bge_api_url=os.getenv("BGE_API_URL", "http://localhost:8080"),
            embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "1536")),
            batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "100")),
            max_retries=int(os.getenv("EMBEDDING_MAX_RETRIES", "3")),
        )

    def validate(self) -> bool:
        """
        验证配置是否有效

        Returns:
            bool: 配置是否有效
        """
        if self.provider not in ("openai", "zhipu", "deepseek", "bge"):
            return False

        if self.provider == "openai" and not self.openai_api_key:
            return False

        if self.provider == "zhipu" and not self.zhipu_api_key:
            return False

        if self.provider == "deepseek" and not self.deepseek_api_key:
            return False

        return True

    def is_openai(self) -> bool:
        """是否使用 OpenAI provider"""
        return self.provider == "openai"

    def is_zhipu(self) -> bool:
        """是否使用智谱 AI (Zhipu) provider"""
        return self.provider == "zhipu"

    def is_deepseek(self) -> bool:
        """是否使用 DeepSeek provider"""
        return self.provider == "deepseek"

    def is_bge(self) -> bool:
        """是否使用 BGE provider"""
        return self.provider == "bge"


# 全局配置实例（延迟初始化）
_embedding_config: Optional[EmbeddingConfig] = None


def get_embedding_config() -> EmbeddingConfig:
    """
    获取 Embedding 配置（单例模式）

    Returns:
        EmbeddingConfig 实例
    """
    global _embedding_config
    if _embedding_config is None:
        _embedding_config = EmbeddingConfig.from_env()
    return _embedding_config


def reload_embedding_config() -> EmbeddingConfig:
    """
    重新加载 Embedding 配置

    Returns:
        重新加载后的 EmbeddingConfig 实例
    """
    global _embedding_config
    _embedding_config = EmbeddingConfig.from_env()
    return _embedding_config
