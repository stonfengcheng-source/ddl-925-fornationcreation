-- pgvector 扩展初始化脚本
-- 用于手动启用向量存储功能
-- 执行方式: psql -U postgres -d data_task_platform -f init_pgvector.sql

-- ============================================
-- 步骤 1: 启用 pgvector 扩展
-- ============================================
CREATE EXTENSION IF NOT EXISTS vector;

-- 验证扩展是否启用
SELECT * FROM pg_extension WHERE extname = 'vector';

-- ============================================
-- 步骤 2: 为 tasks 表添加 embedding 列
-- ============================================
ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- ============================================
-- 步骤 3: 为 datasets 表添加 embedding 列
-- ============================================
ALTER TABLE datasets
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- ============================================
-- 步骤 4: 创建 HNSW 索引 (用于高效相似度搜索)
-- ============================================

-- Tasks 表索引
DROP INDEX IF EXISTS idx_tasks_embedding;
CREATE INDEX idx_tasks_embedding
ON tasks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Datasets 表索引
DROP INDEX IF EXISTS idx_datasets_embedding;
CREATE INDEX idx_datasets_embedding
ON datasets
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ============================================
-- 验证步骤
-- ============================================

-- 查看表结构
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_name = 'tasks'
AND column_name = 'embedding';

SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_name = 'datasets'
AND column_name = 'embedding';

-- 查看索引
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('tasks', 'datasets')
AND indexname LIKE '%embedding%';

-- ============================================
-- 使用说明
-- ============================================
-- 1. 向量插入示例:
--    UPDATE tasks SET embedding = '[0.1, 0.2, ...]'::vector WHERE id = 'xxx';
--
-- 2. 相似度搜索示例 (余弦相似度):
--    SELECT id, task_name, embedding <=> '[0.1, 0.2, ...]'::vector AS distance
--    FROM tasks
--    ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
--    LIMIT 10;
--
-- 3. 使用索引的相似度搜索:
--    SET hnsw.ef_search = 100;
--    SELECT * FROM tasks
--    ORDER BY embedding <=> '[query_vector]'::vector
--    LIMIT 10;
