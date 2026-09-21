import type { EdgeNode, NodeStats, NodeDetail, NodeResourceHistory, NodeTask } from '../types/edgeNode'
import dayjs from 'dayjs'

export const mockEdgeNodes: EdgeNode[] = [
  {
    nodeId: 'NODE-001',
    nodeName: '北京数据中心-节点01',
    status: 'online',
    nodeType: 'training',
    ipAddress: '192.168.1.100',
    port: 8080,
    resources: {
      cpuUsage: 42,
      memoryUsage: 58,
      diskUsage: 65,
      networkBandwidth: 100
    },
    lastHeartbeat: '2026-02-04T10:25:00Z',
    location: {
      province: '北京市',
      city: '海淀区'
    }
  },
  {
    nodeId: 'NODE-002',
    nodeName: '上海数据中心-节点01',
    status: 'offline',
    nodeType: 'validation',
    ipAddress: '192.168.1.101',
    port: 8080,
    resources: {
      cpuUsage: 0,
      memoryUsage: 0,
      diskUsage: 45,
      networkBandwidth: 100
    },
    lastHeartbeat: '2026-02-04T09:15:00Z',
    location: {
      province: '上海市',
      city: '浦东新区'
    }
  },
  {
    nodeId: 'NODE-003',
    nodeName: '广州数据中心-节点01',
    status: 'busy',
    nodeType: 'hybrid',
    ipAddress: '192.168.1.102',
    port: 8080,
    resources: {
      cpuUsage: 85,
      memoryUsage: 78,
      diskUsage: 52,
      networkBandwidth: 200
    },
    lastHeartbeat: '2026-02-04T10:28:00Z',
    location: {
      province: '广东省',
      city: '天河区'
    }
  },
  {
    nodeId: 'NODE-004',
    nodeName: '深圳数据中心-节点01',
    status: 'online',
    nodeType: 'training',
    ipAddress: '192.168.1.103',
    port: 8080,
    resources: {
      cpuUsage: 35,
      memoryUsage: 42,
      diskUsage: 60,
      networkBandwidth: 150
    },
    lastHeartbeat: '2026-02-04T10:30:00Z',
    location: {
      province: '广东省',
      city: '南山区'
    }
  }
]

export const mockNodeStats: NodeStats = {
  totalNodes: 20,
  onlineNodes: 15,
  avgCpuUsage: 42,
  avgMemoryUsage: 58,
  totalBandwidth: 1500
}

export const mockNodeDetail: NodeDetail = {
  nodeId: 'NODE-001',
  nodeName: '北京数据中心-节点01',
  status: 'online',
  nodeType: 'training',
  ipAddress: '192.168.1.100',
  port: 8080,
  location: {
    province: '北京市',
    city: '海淀区',
    district: '中关村街道'
  },
  createdAt: '2026-01-15T10:30:00Z',
  lastHeartbeat: '2026-02-04T10:25:00Z',
  resources: {
    cpuUsage: 42,
    memoryUsage: 58,
    diskUsage: 65,
    currentBandwidth: 50,
    maxBandwidth: 100
  }
}

export const mockNodeTasks: NodeTask[] = [
  {
    taskId: 'TASK-001',
    taskName: '肺癌预测模型训练',
    contribution: 0.35,
    revenue: 15750,
    status: 'completed',
    completedAt: '2026-01-20T14:30:00Z'
  },
  {
    taskId: 'TASK-002',
    taskName: '心脏病风险评估',
    contribution: 0.28,
    revenue: 12400,
    status: 'in_progress',
    completedAt: ''
  }
]

export const mockResourceHistory: NodeResourceHistory = {
  cpu: Array.from({ length: 288 }, (_, i) => ({
    timestamp: dayjs().subtract(24 * 60 - i * 5, 'minute').toISOString(),
    value: Math.floor(Math.random() * 100)
  })),
  memory: Array.from({ length: 288 }, (_, i) => ({
    timestamp: dayjs().subtract(24 * 60 - i * 5, 'minute').toISOString(),
    value: Math.floor(Math.random() * 100)
  })),
  network: Array.from({ length: 288 }, (_, i) => ({
    timestamp: dayjs().subtract(24 * 60 - i * 5, 'minute').toISOString(),
    value: Math.floor(Math.random() * 100)
  }))
}
