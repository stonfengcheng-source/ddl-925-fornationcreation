// 边缘节点类型定义

export interface EdgeNode {
  nodeId: string
  nodeName: string
  status: 'online' | 'offline' | 'busy'
  nodeType: 'training' | 'validation' | 'hybrid'
  ipAddress: string
  port: number
  resources: {
    cpuUsage: number
    memoryUsage: number
    diskUsage: number
    networkBandwidth: number
  }
  lastHeartbeat: string
  location: {
    province: string
    city: string
  }
}

export interface NodeStats {
  totalNodes: number
  onlineNodes: number
  avgCpuUsage: number
  avgMemoryUsage: number
  totalBandwidth: number
}

export interface NodeDetail {
  nodeId: string
  nodeName: string
  status: 'online' | 'offline' | 'busy'
  nodeType: 'training' | 'validation' | 'hybrid'
  ipAddress: string
  port: number
  location: {
    province: string
    city: string
    district: string
  }
  createdAt: string
  lastHeartbeat: string
  resources: {
    cpuUsage: number
    memoryUsage: number
    diskUsage: number
    currentBandwidth: number
    maxBandwidth: number
  }
}

export interface NodeResourceHistory {
  cpu: Array<{ timestamp: string; value: number }>
  memory: Array<{ timestamp: string; value: number }>
  network: Array<{ timestamp: string; value: number }>
}

export interface NodeTask {
  taskId: string
  taskName: string
  contribution: number
  revenue: number
  status: 'completed' | 'in_progress'
  completedAt: string
}

export interface RegisterFormData {
  nodeName: string
  nodeType: 'training' | 'validation' | 'hybrid'
  location: {
    province: string
    city: string
    district: string
  }
  description: string
  ipAddress: string
  port: number
  publicIp: string
  bandwidth: number
  certificateType: 'auto' | 'upload'
  certificate?: File
  privateKey?: File
  agreeToTerms: boolean
}
