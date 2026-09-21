/**
 * 环境/运行时相关类型定义
 */

/**
 * 运行环境模式
 */
export type RuntimeMode = 'web' | 'desktop' | 'mock';

/**
 * 节点部署模式
 */
export type NodeDeployMode = 'local' | 'remote';

/**
 * 本地数据文件信息
 */
export interface DataFileInfo {
  /** 文件完整路径（桌面端）或相对路径 */
  path: string;
  /** 文件名 */
  name: string;
  /** 文件大小（字节） */
  size: number;
  /** 文件扩展名 */
  extension: string;
  /** 行数（可选，大文件可能不计算） */
  rowCount?: number;
  /** 列数 */
  columnCount?: number;
  /** 预览数据（前N行） */
  preview: string[][];
}

/**
 * 本地节点配置
 */
export interface LocalNodeConfig {
  node_id: string;
  node_name: string;
  aggregator_url: string;
  certificate_path?: string;
  data_directory: string;
}

/**
 * 本地训练配置
 */
export interface LocalTrainingConfig {
  /** 数据文件路径 */
  data_path: string;
  /** 目标列名 */
  target_column: string;
  /** 最大训练轮次 */
  max_rounds?: number;
  /** 目标准确率 */
  target_accuracy?: number;
  /** 本地训练epochs */
  local_epochs?: number;
}

/**
 * 本地训练状态
 */
export interface LocalTrainingStatus {
  /** 是否正在训练 */
  is_training: boolean;
  /** 当前轮次 */
  current_round: number;
  /** 训练指标 */
  metrics?: {
    loss: number;
    accuracy: number;
    round: number;
  };
}

/**
 * Python服务健康状态
 */
export interface PythonHealthStatus {
  status: 'healthy' | 'unhealthy';
  version: string;
  training: boolean;
  node_id?: string;
}
