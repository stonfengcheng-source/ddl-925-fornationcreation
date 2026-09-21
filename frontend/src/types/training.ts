// 联邦训练任务状态
export type TrainingStatus =
  | 'pending'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

// 节点状态
export type NodeStatus =
  | 'online'
  | 'offline'
  | 'training'
  | 'error'
  | 'syncing';

// 训练任务基本信息
export interface TrainingTask {
  id: string;
  name: string;
  description: string;
  status: TrainingStatus;
  createdAt: string;
  updatedAt: string;
  startedAt?: string;
  completedAt?: string;
  ownerId: string;
  ownerName: string;
  modelType: string;
  datasetId: string;
  datasetName: string;
  totalRounds: number;
  currentRound: number;
  targetAccuracy: number;
  currentAccuracy?: number;
  participantCount: number;
  rewardPool: number;
  rewardCurrency: string;
}

// 训练节点/参与方
export interface TrainingNode {
  id: string;
  name: string;
  nodeId: string;
  status: NodeStatus;
  role: 'aggregator' | 'trainer' | 'validator';
  taskId: string;
  joinedAt: string;
  lastHeartbeat: string;
  dataSampleCount: number;
  contributionScore: number;
  earnedReward: number;
  latency: number; // ms
  computePower: number; // FLOPS
  currentRound?: number;
  trainingProgress?: number; // 0-100
}

// 训练指标（单轮）
export interface RoundMetrics {
  round: number;
  timestamp: string;
  globalLoss: number;
  globalAccuracy: number;
  validationLoss?: number;
  validationAccuracy?: number;
  participatingNodes: number;
  aggregationTime: number; // ms
}

// 训练指标时间序列
export interface TrainingMetrics {
  taskId: string;
  metrics: RoundMetrics[];
  currentRound: number;
  totalRounds: number;
  estimatedTimeRemaining?: number; // seconds
}

// 节点贡献度详情
export interface NodeContribution {
  nodeId: string;
  nodeName: string;
  taskId: string;
  dataQualityScore: number; // 0-100
  dataQuantityScore: number; // 0-100
  computationScore: number; // 0-100
  timelinessScore: number; // 0-100
  overallScore: number; // 0-100
  sampleCount: number;
  roundsParticipated: number;
  rewardAmount: number;
  lastUpdated: string;
}

// 分账记录
export interface RevenueShareRecord {
  id: string;
  taskId: string;
  taskName: string;
  nodeId: string;
  nodeName: string;
  round: number;
  contributionScore: number;
  sharePercentage: number;
  amount: number;
  currency: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  createdAt: string;
  settledAt?: string;
  transactionHash?: string;
}

// 结算统计
export interface SettlementSummary {
  taskId: string;
  totalReward: number;
  distributedReward: number;
  pendingReward: number;
  nodeCount: number;
  completedRounds: number;
  startTime: string;
  endTime?: string;
}

// 实时监控数据
export interface RealTimeTrainingStats {
  taskId: string;
  timestamp: string;
  activeNodes: number;
  totalNodes: number;
  currentRound: number;
  roundProgress: number; // 0-100
  latestLoss: number;
  latestAccuracy: number;
  networkLatency: number; // avg ms
  throughput: number; // samples/sec
}

// 训练配置
export interface TrainingConfig {
  taskId: string;
  modelType: string;
  optimizer: string;
  learningRate: number;
  batchSize: number;
  epochs: number;
  aggregationStrategy: 'fedavg' | 'fedprox' | 'scaffold';
  minNodes: number;
  maxNodes: number;
  timeoutPerRound: number; // seconds
  targetAccuracy?: number;
  maxRounds: number;
  differentialPrivacy?: {
    enabled: boolean;
    epsilon?: number;
    delta?: number;
  };
}

// 训练日志
export interface TrainingLog {
  id: string;
  taskId: string;
  nodeId?: string;
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
  round?: number;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

// 任务筛选条件
export interface TrainingTaskFilter {
  status?: TrainingStatus[];
  ownerId?: string;
  modelType?: string;
  startDateFrom?: string;
  startDateTo?: string;
  keyword?: string;
}

// 分账筛选条件
export interface RevenueShareFilter {
  taskId?: string;
  nodeId?: string;
  status?: string[];
  dateFrom?: string;
  dateTo?: string;
}

// 分页响应
export interface PaginatedResponse<T> {
  list: T[];
  total: number;
  page: number;
  pageSize: number;
}

// 训练任务创建请求
export interface CreateTrainingTaskRequest {
  name: string;
  description?: string;
  modelType: string;
  datasetId: string;
  totalRounds: number;
  targetAccuracy?: number;
  rewardPool: number;
  rewardCurrency: string;
  config: Omit<TrainingConfig, 'taskId'>;
}

// ==================== 语义匹配相关类型 ====================

// 匹配分数详情
export interface MatchScore {
  total: number;      // 综合评分 (0-1)
  semantic: number;   // 语义相似度 (0-1)
  tag: number;        // 标签匹配度 (0-1)
  quantity: number;   // 数据量匹配度 (0-1)
}

// 语义推荐任务（Provider视角）
export interface RecommendedTask {
  task_id: string;
  task_name: string;
  description?: string;
  category?: string;
  reward_pool: number;
  scores: MatchScore;
  status: string;
  min_samples?: number;
  max_nodes?: number;
  current_participants?: number;
  already_joined: boolean;
  created_at?: string;
}

// 匹配的数据集（Buyer视角）
export interface MatchingDataset {
  dataset_id: string;
  dataset_name: string;
  description?: string;
  data_type?: string;
  row_count?: number;
  owner_id?: string;
  scores: MatchScore;
}

// 语义匹配结果响应
export interface MatchingDatasetsResponse {
  task_id: string;
  task_name: string;
  matches: MatchingDataset[];
}

// 训练任务详情（包含完整信息）
export interface TrainingTaskDetail extends TrainingTask {
  nodes: TrainingNode[];
  metrics: TrainingMetrics;
  config: TrainingConfig;
  settlementSummary: SettlementSummary;
}

// ==================== 隐私预算相关类型 ====================

// 隐私预算消耗记录
export interface PrivacyBudgetConsumption {
  round: number;
  epsilonConsumed: number;      // 本轮消耗
  epsilonCumulative: number;    // 累计消耗
  delta: number;
  timestamp: string;
  nodeId?: string;              // 节点ID（多节点场景）
}

// 节点隐私预算状态
export interface NodePrivacyBudget {
  nodeId: string;
  nodeName: string;
  epsilonTotal: number;
  epsilonConsumed: number;
  epsilonRemaining: number;
  delta: number;
  consumptionHistory: PrivacyBudgetConsumption[];
  status: 'safe' | 'warning' | 'exhausted';
}

// 任务隐私预算概览
export interface TaskPrivacyBudgetSummary {
  taskId: string;
  epsilonTotal: number;
  epsilonConsumed: number;
  epsilonRemaining: number;
  delta: number;
  nodeBudgets: NodePrivacyBudget[];
  estimatedRoundsRemaining: number;
  consumptionTrend: PrivacyBudgetConsumption[];
}

// 隐私预算卡片组件Props
export interface PrivacyBudgetCardProps {
  epsilon: number;           // 总预算
  epsilonConsumed: number;   // 已消耗预算
  delta: number;             // 隐私失败概率
  threshold?: number;        // 警告阈值 (默认80%)
  showProgress?: boolean;    // 是否显示进度条
  size?: 'small' | 'medium' | 'large';
  nodeName?: string;         // 节点名称（可选）
}

// 隐私预算趋势图组件Props
export interface PrivacyBudgetTrendChartProps {
  data: PrivacyBudgetConsumption[];
  totalBudget: number;       // 总预算（用于显示参考线）
  height?: number;
  title?: string;
}
