/**
 * MSW Mock Handlers
 * 支持三种数据源：云端API、本地API、Mock数据
 *
 * 注意：需要安装 msw 包才能使用
 * npm install msw --save-dev
 */

// 本地API Mock数据（桌面端开发用）
export const localMockData = {
  // 健康检查
  health: {
    status: 'healthy',
    version: '1.0.0',
    training: false,
  },

  // 本地数据文件列表
  dataFiles: {
    files: [
      {
        path: '/workspace/node-001/data.csv',
        name: 'training_data.csv',
        size: 1024000,
        extension: 'csv',
        rowCount: 10000,
        columnCount: 15,
        preview: [
          ['id', 'feature1', 'feature2', 'target'],
          ['1', '0.5', '0.3', '1'],
          ['2', '0.2', '0.8', '0'],
        ],
      },
    ],
  },

  // 数据预览
  dataPreview: {
    preview: [
      ['id', 'feature1', 'feature2', 'target'],
      ['1', '0.5', '0.3', '1'],
      ['2', '0.2', '0.8', '0'],
    ],
    columns: ['id', 'feature1', 'feature2', 'target'],
    total_rows: 10000,
  },

  // 训练状态
  trainingStatus: {
    is_training: true,
    current_round: 5,
    metrics: {
      loss: 0.234,
      accuracy: 0.876,
      round: 5,
    },
  },

  // 启动训练响应
  trainingStart: { status: 'started' },

  // 停止训练响应
  trainingStop: { status: 'stopped' },

  // 初始化节点响应
  nodeInit: { status: 'initialized' },
};

/**
 * 创建 MSW handlers
 * 在 msw 安装后取消下面的注释
 */
export const handlers: unknown[] = [];

// 当安装 msw 后，使用以下实现：
/*
import { http, HttpResponse } from 'msw';

export const handlers = [
  // 健康检查
  http.get('http://localhost:8765/health', () => {
    return HttpResponse.json(localMockData.health);
  }),

  // 本地数据文件列表
  http.get('http://localhost:8765/api/data/files', () => {
    return HttpResponse.json(localMockData.dataFiles);
  }),

  // 数据预览
  http.post('http://localhost:8765/api/data/preview', () => {
    return HttpResponse.json(localMockData.dataPreview);
  }),

  // 训练状态
  http.get('http://localhost:8765/api/training/status', () => {
    return HttpResponse.json(localMockData.trainingStatus);
  }),

  // 启动训练
  http.post('http://localhost:8765/api/training/start', () => {
    return HttpResponse.json(localMockData.trainingStart);
  }),

  // 停止训练
  http.post('http://localhost:8765/api/training/stop', () => {
    return HttpResponse.json(localMockData.trainingStop);
  }),

  // 初始化节点
  http.post('http://localhost:8765/api/node/init', () => {
    return HttpResponse.json(localMockData.nodeInit);
  }),
];
*/

export default handlers;
