/**
 * 训练前数据价值预评估 API 服务
 * 提供基于数据特征的贡献度预估功能
 */

import request from '../request';

export interface ProviderPreEstimate {
  provider_id: string;
  provider_name: string;
  data_volume: number;
  quality_score: number;
  diversity_score: number;
  estimated_ratio: number;
  estimated_amount: number;
}

export interface PreEstimateResponse {
  task_id: string;
  reward_pool: number;
  providers: ProviderPreEstimate[];
}

/**
 * 获取任务训练前数据价值预评估
 * @param taskId 任务ID
 * @returns 预评估结果
 */
export const getPreEstimate = async (
  taskId: string
): Promise<{ data: PreEstimateResponse; meta?: Record<string, unknown> }> => {
  return request.get(`/tasks/${taskId}/pre-estimate`) as Promise<{
    data: PreEstimateResponse;
    meta?: Record<string, unknown>;
  }>;
};

/**
 * 启动联邦学习训练
 * @param taskId 任务ID
 * @returns 启动结果
 */
export const startTraining = async (
  taskId: string
): Promise<{ data: { message: string; task_id: string }; meta?: Record<string, unknown> }> => {
  return request.post(`/training/${taskId}/start`) as Promise<{
    data: { message: string; task_id: string };
    meta?: Record<string, unknown>;
  }>;
};
