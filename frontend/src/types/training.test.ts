import { describe, it, expect } from 'vitest';
import {
  TrainingTask,
  TrainingNode,
  TrainingMetrics,
  NodeContribution,
  RevenueShareRecord,
  SettlementSummary,
} from './training';

describe('Training Types', () => {
  it('should define TrainingTask interface', () => {
    const task: Partial<TrainingTask> = {
      id: 'TASK-001',
      name: '测试任务',
      status: 'running',
      totalRounds: 100,
      currentRound: 50,
    };
    expect(task.id).toBe('TASK-001');
    expect(task.status).toBe('running');
  });

  it('should define TrainingNode interface', () => {
    const node: Partial<TrainingNode> = {
      id: 'NODE-001',
      name: '测试节点',
      status: 'training',
      role: 'trainer',
      contributionScore: 85.5,
    };
    expect(node.role).toBe('trainer');
    expect(node.contributionScore).toBe(85.5);
  });

  it('should define RevenueShareRecord interface', () => {
    const record: Partial<RevenueShareRecord> = {
      id: 'SHARE-001',
      amount: 1000,
      currency: 'CNY',
      status: 'completed',
    };
    expect(record.status).toBe('completed');
    expect(record.amount).toBe(1000);
  });
});
