/**
 * 数据集模块 Mock 数据
 */

// 数据集状态类型
export type DatasetStatus = 'ready' | 'processing' | 'error' | 'uploading';

// 数据集类型
export type DatasetType = 'csv' | 'json' | 'parquet' | 'excel';

// 列数据类型
export type ColumnType = 'string' | 'number' | 'boolean' | 'datetime' | 'category';

// 数据集接口
export interface Dataset {
  id: string;
  name: string;
  description: string;
  type: DatasetType;
  status: DatasetStatus;
  size: number; // 字节
  rowCount: number;
  columnCount: number;
  createdAt: string;
  updatedAt: string;
  tags: string[];
  owner: string;
  avatar?: string;
  qualityScore?: number; // 0-100
  usageCount: number;
}

// 列信息接口
export interface ColumnInfo {
  name: string;
  type: ColumnType;
  nullable: boolean;
  uniqueCount: number;
  nullCount: number;
  sampleValues: (string | number | boolean)[];
  isIndex?: boolean;
  statistics?: {
    min?: number;
    max?: number;
    mean?: number;
    std?: number;
    median?: number;
  };
}

// 数据集详情接口
export interface DatasetDetail extends Dataset {
  columns: ColumnInfo[];
  previewData: Record<string, unknown>[];
  statistics: {
    totalSize: number;
    fileCount: number;
    completeness: number; // 完整度百分比
    consistency: number; // 一致性百分比
    accuracy: number; // 准确度百分比
  };
  schema: {
    version: string;
    primaryKey?: string;
    description?: string;
  };
}

// 上传任务接口
export interface UploadTask {
  id: string;
  fileName: string;
  size: number;
  progress: number;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error';
  errorMessage?: string;
  columnConfig?: ColumnConfig[];
}

// 列配置接口
export interface ColumnConfig {
  name: string;
  type: ColumnType;
  isTarget: boolean;
  isFeature: boolean;
  isIndex: boolean;
  description?: string;
}

// 模拟数据集列表
export const mockDatasets: Dataset[] = [
  {
    id: 'DS-001',
    name: '客户购买行为数据集',
    description: '包含 10 万条客户购买记录，用于分析用户消费行为和偏好预测',
    type: 'csv',
    status: 'ready',
    size: 15_728_640, // 15MB
    rowCount: 100000,
    columnCount: 24,
    createdAt: '2024-01-15 10:30:00',
    updatedAt: '2024-01-20 14:20:00',
    tags: ['电商', '用户行为', '推荐系统'],
    owner: '张三',
    qualityScore: 92,
    usageCount: 156,
  },
  {
    id: 'DS-002',
    name: '医疗影像标注数据',
    description: '肺部 CT 影像数据集，包含 5000 张标注影像，用于肺癌早期检测模型训练',
    type: 'json',
    status: 'ready',
    size: 2_147_483_648, // 2GB
    rowCount: 5000,
    columnCount: 8,
    createdAt: '2024-01-10 09:00:00',
    updatedAt: '2024-01-18 16:45:00',
    tags: ['医疗', '影像', '深度学习'],
    owner: '李医生',
    qualityScore: 88,
    usageCount: 89,
  },
  {
    id: 'DS-003',
    name: '金融交易风控数据',
    description: '银行交易记录数据集，包含欺诈检测标签，用于风控模型训练',
    type: 'parquet',
    status: 'processing',
    size: 536_870_912, // 512MB
    rowCount: 500000,
    columnCount: 42,
    createdAt: '2024-01-22 11:00:00',
    updatedAt: '2024-01-22 11:30:00',
    tags: ['金融', '风控', '欺诈检测'],
    owner: '王分析师',
    usageCount: 0,
  },
  {
    id: 'DS-004',
    name: '交通流量监测数据',
    description: '城市道路传感器采集的实时交通流量数据',
    type: 'csv',
    status: 'ready',
    size: 104_857_600, // 100MB
    rowCount: 2000000,
    columnCount: 12,
    createdAt: '2024-01-05 08:00:00',
    updatedAt: '2024-01-19 20:00:00',
    tags: ['交通', 'IoT', '时序数据'],
    owner: '赵工程师',
    qualityScore: 85,
    usageCount: 234,
  },
  {
    id: 'DS-005',
    name: '社交媒体情感分析数据',
    description: '微博评论数据集，包含情感标注，用于情感分析模型训练',
    type: 'json',
    status: 'error',
    size: 52_428_800, // 50MB
    rowCount: 150000,
    columnCount: 6,
    createdAt: '2024-01-20 15:00:00',
    updatedAt: '2024-01-21 09:00:00',
    tags: ['NLP', '情感分析', '社交媒体'],
    owner: '钱研究员',
    usageCount: 12,
  },
  {
    id: 'DS-006',
    name: '零售销售预测数据',
    description: '连锁超市历史销售数据，包含促销信息和外部因素',
    type: 'excel',
    status: 'ready',
    size: 26_214_400, // 25MB
    rowCount: 50000,
    columnCount: 35,
    createdAt: '2024-01-12 14:00:00',
    updatedAt: '2024-01-16 10:30:00',
    tags: ['零售', '销售预测', '时序分析'],
    owner: '孙经理',
    qualityScore: 90,
    usageCount: 78,
  },
  {
    id: 'DS-007',
    name: '工业设备传感器数据',
    description: '工厂设备传感器采集的振动、温度等数据，用于预测性维护',
    type: 'csv',
    status: 'ready',
    size: 314_572_800, // 300MB
    rowCount: 10000000,
    columnCount: 18,
    createdAt: '2024-01-08 06:00:00',
    updatedAt: '2024-01-17 18:00:00',
    tags: ['工业', 'IoT', '预测维护'],
    owner: '周工程师',
    qualityScore: 87,
    usageCount: 145,
  },
  {
    id: 'DS-008',
    name: '教育学习行为数据',
    description: '在线教育平台学生学习行为数据，用于学习效果分析',
    type: 'json',
    status: 'ready',
    size: 78_643_200, // 75MB
    rowCount: 300000,
    columnCount: 28,
    createdAt: '2024-01-14 09:30:00',
    updatedAt: '2024-01-19 11:00:00',
    tags: ['教育', '学习分析', '行为数据'],
    owner: '吴老师',
    qualityScore: 91,
    usageCount: 67,
  },
];

// 模拟数据集详情
export const mockDatasetDetail: DatasetDetail = {
  ...mockDatasets[0],
  columns: [
    {
      name: 'user_id',
      type: 'string',
      nullable: false,
      uniqueCount: 50000,
      nullCount: 0,
      sampleValues: ['U001', 'U002', 'U003'],
    },
    {
      name: 'age',
      type: 'number',
      nullable: false,
      uniqueCount: 60,
      nullCount: 0,
      sampleValues: [25, 34, 45],
      statistics: { min: 18, max: 80, mean: 35.5, std: 12.3, median: 32 },
    },
    {
      name: 'gender',
      type: 'category',
      nullable: false,
      uniqueCount: 2,
      nullCount: 0,
      sampleValues: ['M', 'F'],
    },
    {
      name: 'purchase_amount',
      type: 'number',
      nullable: false,
      uniqueCount: 8500,
      nullCount: 0,
      sampleValues: [299.99, 1500.0, 89.5],
      statistics: { min: 9.9, max: 99999, mean: 1250.5, std: 3500.2, median: 599.0 },
    },
    {
      name: 'purchase_date',
      type: 'datetime',
      nullable: false,
      uniqueCount: 50000,
      nullCount: 0,
      sampleValues: ['2024-01-15', '2024-01-16', '2024-01-17'],
    },
    {
      name: 'category',
      type: 'category',
      nullable: false,
      uniqueCount: 15,
      nullCount: 0,
      sampleValues: ['电子产品', '服装', '食品'],
    },
    {
      name: 'is_member',
      type: 'boolean',
      nullable: false,
      uniqueCount: 2,
      nullCount: 0,
      sampleValues: [true, false],
    },
    {
      name: 'discount_rate',
      type: 'number',
      nullable: true,
      uniqueCount: 20,
      nullCount: 15000,
      sampleValues: [0.1, 0.2, 0.0],
      statistics: { min: 0, max: 0.5, mean: 0.15, std: 0.12, median: 0.1 },
    },
  ],
  previewData: [
    {
      user_id: 'U001',
      age: 25,
      gender: 'M',
      purchase_amount: 299.99,
      purchase_date: '2024-01-15',
      category: '电子产品',
      is_member: true,
      discount_rate: 0.1,
    },
    {
      user_id: 'U002',
      age: 34,
      gender: 'F',
      purchase_amount: 1500.0,
      purchase_date: '2024-01-16',
      category: '服装',
      is_member: false,
      discount_rate: 0.2,
    },
    {
      user_id: 'U003',
      age: 45,
      gender: 'M',
      purchase_amount: 89.5,
      purchase_date: '2024-01-17',
      category: '食品',
      is_member: true,
      discount_rate: 0.0,
    },
    {
      user_id: 'U004',
      age: 28,
      gender: 'F',
      purchase_amount: 599.0,
      purchase_date: '2024-01-18',
      category: '电子产品',
      is_member: true,
      discount_rate: 0.15,
    },
    {
      user_id: 'U005',
      age: 52,
      gender: 'M',
      purchase_amount: 1200.0,
      purchase_date: '2024-01-19',
      category: '家居',
      is_member: false,
      discount_rate: null,
    },
    {
      user_id: 'U006',
      age: 31,
      gender: 'F',
      purchase_amount: 350.5,
      purchase_date: '2024-01-20',
      category: '美妆',
      is_member: true,
      discount_rate: 0.1,
    },
    {
      user_id: 'U007',
      age: 38,
      gender: 'M',
      purchase_amount: 899.99,
      purchase_date: '2024-01-21',
      category: '电子产品',
      is_member: true,
      discount_rate: 0.25,
    },
    {
      user_id: 'U008',
      age: 26,
      gender: 'F',
      purchase_amount: 199.0,
      purchase_date: '2024-01-22',
      category: '服装',
      is_member: false,
      discount_rate: 0.0,
    },
  ],
  statistics: {
    totalSize: 15_728_640,
    fileCount: 1,
    completeness: 98.5,
    consistency: 95.2,
    accuracy: 92.8,
  },
  schema: {
    version: '1.0.0',
    primaryKey: 'user_id',
    description: '客户购买行为数据标准Schema',
  },
};

// 模拟上传任务
export const mockUploadTasks: UploadTask[] = [
  {
    id: 'UP-001',
    fileName: 'sales_data_2024.csv',
    size: 52_428_800,
    progress: 100,
    status: 'completed',
    columnConfig: [
      { name: 'date', type: 'datetime', isTarget: false, isFeature: true, isIndex: false },
      { name: 'product_id', type: 'string', isTarget: false, isFeature: true, isIndex: false },
      { name: 'quantity', type: 'number', isTarget: false, isFeature: true, isIndex: false },
      { name: 'revenue', type: 'number', isTarget: true, isFeature: false, isIndex: false },
    ],
  },
  {
    id: 'UP-002',
    fileName: 'customer_survey.json',
    size: 10_485_760,
    progress: 75,
    status: 'uploading',
  },
];

// 文件类型配置
export const fileTypeConfig: Record<DatasetType, { icon: string; color: string; accept: string }> = {
  csv: { icon: 'FileTextOutlined', color: '#52c41a', accept: '.csv' },
  json: { icon: 'FileJsonOutlined', color: '#faad14', accept: '.json' },
  parquet: { icon: 'DatabaseOutlined', color: '#722ed1', accept: '.parquet' },
  excel: { icon: 'FileExcelOutlined', color: '#13c2c2', accept: '.xlsx,.xls' },
};

// 数据集分类标签
export const datasetTags = [
  '电商', '医疗', '金融', '交通', '工业', '教育',
  'NLP', '图像', '时序', '推荐', '风控', 'IoT',
  '用户行为', '销售预测', '情感分析', '深度学习',
];

// 格式化文件大小
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 格式化数字
export function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
}
