import type {
  PrivacyBudgetConsumption,
  NodePrivacyBudget,
  TaskPrivacyBudgetSummary,
} from '@/types/training';

// 生成隐私预算消费历史（模拟67轮训练的数据）
const generateConsumptionHistory = (
  nodeId: string,
  totalRounds: number,
  epsilonPerRound: number
): PrivacyBudgetConsumption[] => {
  const history: PrivacyBudgetConsumption[] = [];
  let cumulative = 0;

  for (let i = 1; i <= totalRounds; i++) {
    // 模拟每轮消耗的epsilon略有波动
    const roundConsumption = epsilonPerRound * (0.9 + Math.random() * 0.2);
    cumulative += roundConsumption;

    history.push({
      round: i,
      epsilonConsumed: Number(roundConsumption.toFixed(4)),
      epsilonCumulative: Number(cumulative.toFixed(4)),
      delta: 0.0001,
      timestamp: new Date(Date.now() - (totalRounds - i) * 10 * 60 * 1000).toISOString(),
      nodeId,
    });
  }

  return history;
};

// Mock 节点隐私预算状态
const mockNodeBudgets: NodePrivacyBudget[] = [
  {
    nodeId: 'NODE-001',
    nodeName: '北京协和医院',
    epsilonTotal: 2.0,
    epsilonConsumed: 1.34,
    epsilonRemaining: 0.66,
    delta: 0.0001,
    consumptionHistory: generateConsumptionHistory('NODE-001', 67, 0.02),
    status: 'safe',
  },
  {
    nodeId: 'NODE-002',
    nodeName: '上海瑞金医院',
    epsilonTotal: 1.5,
    epsilonConsumed: 1.20,
    epsilonRemaining: 0.30,
    delta: 0.0001,
    consumptionHistory: generateConsumptionHistory('NODE-002', 67, 0.018),
    status: 'warning',
  },
  {
    nodeId: 'NODE-003',
    nodeName: '广州中山医院',
    epsilonTotal: 1.0,
    epsilonConsumed: 0.52,
    epsilonRemaining: 0.48,
    delta: 0.0001,
    consumptionHistory: generateConsumptionHistory('NODE-003', 67, 0.008),
    status: 'safe',
  },
  {
    nodeId: 'NODE-004',
    nodeName: '中心聚合节点',
    epsilonTotal: 0.5,
    epsilonConsumed: 0.29,
    epsilonRemaining: 0.21,
    delta: 0.0001,
    consumptionHistory: generateConsumptionHistory('NODE-004', 67, 0.004),
    status: 'safe',
  },
  {
    nodeId: 'NODE-005',
    nodeName: '深圳人民医院',
    epsilonTotal: 1.0,
    epsilonConsumed: 0.95,
    epsilonRemaining: 0.05,
    delta: 0.0001,
    consumptionHistory: generateConsumptionHistory('NODE-005', 67, 0.014),
    status: 'exhausted',
  },
];

// Mock 全局消费趋势（汇总所有节点）
const generateGlobalConsumptionTrend = (
  totalRounds: number
): PrivacyBudgetConsumption[] => {
  const trend: PrivacyBudgetConsumption[] = [];
  let cumulative = 0;

  for (let i = 1; i <= totalRounds; i++) {
    // 汇总所有节点的消费
    const roundConsumption =
      0.02 * (0.9 + Math.random() * 0.2) +
      0.018 * (0.9 + Math.random() * 0.2) +
      0.008 * (0.9 + Math.random() * 0.2) +
      0.004 * (0.9 + Math.random() * 0.2) +
      0.014 * (0.9 + Math.random() * 0.2);

    cumulative += roundConsumption;

    trend.push({
      round: i,
      epsilonConsumed: Number(roundConsumption.toFixed(4)),
      epsilonCumulative: Number(cumulative.toFixed(4)),
      delta: 0.0001,
      timestamp: new Date(Date.now() - (totalRounds - i) * 10 * 60 * 1000).toISOString(),
    });
  }

  return trend;
};

// 计算任务总体预算状态
const calculateTaskSummary = (): TaskPrivacyBudgetSummary => {
  const totalEpsilon = mockNodeBudgets.reduce(
    (sum, node) => sum + node.epsilonTotal,
    0
  );
  const consumedEpsilon = mockNodeBudgets.reduce(
    (sum, node) => sum + node.epsilonConsumed,
    0
  );
  const remainingEpsilon = totalEpsilon - consumedEpsilon;
  const avgConsumptionPerRound = consumedEpsilon / 67;
  const estimatedRoundsRemaining =
    avgConsumptionPerRound > 0
      ? Math.floor(remainingEpsilon / avgConsumptionPerRound)
      : 0;

  return {
    taskId: 'TASK-001',
    epsilonTotal: Number(totalEpsilon.toFixed(3)),
    epsilonConsumed: Number(consumedEpsilon.toFixed(3)),
    epsilonRemaining: Number(remainingEpsilon.toFixed(3)),
    delta: 0.0001,
    nodeBudgets: mockNodeBudgets,
    estimatedRoundsRemaining,
    consumptionTrend: generateGlobalConsumptionTrend(67),
  };
};

// Mock 任务隐私预算汇总
export const mockPrivacyBudgetSummary: TaskPrivacyBudgetSummary =
  calculateTaskSummary();

// Mock 全局隐私预算仪表盘数据
export const mockGlobalPrivacyBudgetStats = {
  totalTasks: 12,
  activeTasks: 5,
  totalEpsilonAllocated: 25.0,
  totalEpsilonConsumed: 18.65,
  totalEpsilonRemaining: 6.35,
  nodesWithWarning: 3,
  nodesExhausted: 1,
  avgConsumptionRate: 74.6,
  consumptionTrend: generateGlobalConsumptionTrend(67),
};

// 导出所有Mock数据
export const privacyBudgetMock = {
  summary: mockPrivacyBudgetSummary,
  nodeBudgets: mockNodeBudgets,
  globalStats: mockGlobalPrivacyBudgetStats,
};

export default privacyBudgetMock;
