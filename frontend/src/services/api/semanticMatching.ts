/**
 * 语义匹配 API 服务
 * 提供基于向量相似度的智能推荐功能
 */
import request from '../request';
import type { RecommendedTask, MatchingDatasetsResponse } from '@/types/training';

/**
 * 获取语义推荐的任务（Provider 视角）
 * @param topK 返回结果数量
 * @param minSimilarity 最小相似度阈值 (0-1)
 * @returns 推荐任务列表
 */
export const getRecommendedTasksSemantic = async (
  topK: number = 10,
  minSimilarity: number = 0.0
): Promise<{ data: RecommendedTask[]; meta?: Record<string, unknown> }> => {
  return request.get('/training/recommended-semantic', {
    params: {
      top_k: topK,
      min_similarity: minSimilarity,
    },
  }) as Promise<{ data: RecommendedTask[]; meta?: Record<string, unknown> }>;
};

/**
 * 获取任务匹配的数据集（Buyer 视角）
 * @param taskId 任务ID
 * @param topK 返回结果数量
 * @param minSimilarity 最小相似度阈值 (0-1)
 * @returns 匹配的数据集列表
 */
export const getMatchingDatasetsForTask = async (
  taskId: string,
  topK: number = 10,
  minSimilarity: number = 0.0
): Promise<{ data: MatchingDatasetsResponse; meta?: Record<string, unknown> }> => {
  return request.get(`/training/${taskId}/matching-datasets`, {
    params: {
      top_k: topK,
      min_similarity: minSimilarity,
    },
  }) as Promise<{ data: MatchingDatasetsResponse; meta?: Record<string, unknown> }>;
};
