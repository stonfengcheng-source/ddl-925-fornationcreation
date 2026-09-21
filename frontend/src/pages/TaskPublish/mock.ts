/**
 * TaskPublish 页面 Mock 数据
 * 任务发布向导使用的模拟数据
 */

// 模型类型选项
export const mockModelTypes = [
  { value: 'ResNet50', label: 'ResNet50', description: '经典残差网络，适用于图像分类' },
  { value: 'ResNet101', label: 'ResNet101', description: '深层残差网络，精度更高' },
  { value: 'VGG16', label: 'VGG16', description: '经典卷积网络，结构简单' },
  { value: 'VGG19', label: 'VGG19', description: '深层VGG网络' },
  { value: 'MobileNetV2', label: 'MobileNetV2', description: '轻量级网络，适合移动端' },
  { value: 'EfficientNetB0', label: 'EfficientNetB0', description: '高效网络，精度与速度平衡' },
  { value: 'XGBoost', label: 'XGBoost', description: '梯度提升树，适合表格数据' },
  { value: 'LightGBM', label: 'LightGBM', description: '微软开源GBDT框架' },
  { value: 'DeepFM', label: 'DeepFM', description: '深度学习推荐模型' },
  { value: 'Wide&Deep', label: 'Wide&Deep', description: '谷歌推荐模型' },
  { value: 'Transformer', label: 'Transformer', description: '注意力机制模型' },
  { value: 'BERT', label: 'BERT', description: '预训练语言模型' },
  { value: 'Wave2Vec2', label: 'Wave2Vec2', description: '语音表示学习模型' },
  { value: 'AutoEncoder', label: 'AutoEncoder', description: '自编码器，适合异常检测' },
];

// 优化器选项
export const mockOptimizers = [
  { value: 'Adam', label: 'Adam', description: '自适应矩估计，最常用的优化器' },
  { value: 'SGD', label: 'SGD', description: '随机梯度下降，适合大规模数据' },
  { value: 'RMSprop', label: 'RMSprop', description: '均方根传播，适合RNN' },
  { value: 'Adagrad', label: 'Adagrad', description: '自适应梯度，适合稀疏数据' },
  { value: 'AdamW', label: 'AdamW', description: '带权重衰减的Adam' },
];

// 聚合策略选项
export const mockAggregationStrategies = [
  {
    value: 'fedavg',
    label: 'FedAvg',
    description: '联邦平均算法，最常用的聚合策略，简单高效',
    pros: ['实现简单', '收敛稳定', '通信开销小'],
    cons: ['非独立同分布数据效果一般', '可能存在客户端漂移'],
  },
  {
    value: 'fedprox',
    label: 'FedProx',
    description: '近端联邦优化，通过近端项限制本地更新幅度',
    pros: ['适合异构数据', '收敛更稳定', '支持非独立同分布'],
    cons: ['需要调优近端参数', '计算开销略大'],
  },
  {
    value: 'scaffold',
    label: 'SCAFFOLD',
    description: '随机控制平均联邦学习，使用控制变量纠正客户端漂移',
    pros: ['收敛速度快', '适合大规模联邦学习', '理论保证强'],
    cons: ['需要存储控制变量', '内存开销较大'],
  },
  {
    value: 'fednova',
    label: 'FedNova',
    description: '归一化平均，解决不同客户端本地轮次不一致问题',
    pros: ['支持异构本地轮次', '公平性更好'],
    cons: ['实现较复杂', '需要额外归一化计算'],
  },
];

// 数据格式选项
export const mockDataFormats = [
  { value: 'CSV', label: 'CSV', description: '逗号分隔值，适合表格数据' },
  { value: 'JSON', label: 'JSON', description: 'JSON格式，适合结构化数据' },
  { value: 'Parquet', label: 'Parquet', description: '列式存储格式，适合大数据' },
  { value: 'TFRecord', label: 'TFRecord', description: 'TensorFlow专用格式' },
  { value: 'HDF5', label: 'HDF5', description: '层次数据格式，适合科学数据' },
  { value: 'DICOM', label: 'DICOM', description: '医学影像标准格式' },
  { value: 'NIfTI', label: 'NIfTI', description: '神经影像学格式' },
  { value: 'PNG', label: 'PNG', description: '无损压缩图像格式' },
  { value: 'JPEG', label: 'JPEG', description: '有损压缩图像格式' },
  { value: 'WAV', label: 'WAV', description: '音频波形格式' },
  { value: 'MP3', label: 'MP3', description: '压缩音频格式' },
  { value: 'Text', label: 'Text', description: '纯文本格式' },
];

// 任务类别选项
export const mockTaskCategories = [
  { value: 'healthcare', label: '医疗健康', icon: 'MedicineBoxOutlined', color: '#52c41a' },
  { value: 'finance', label: '金融科技', icon: 'BankOutlined', color: '#faad14' },
  { value: 'retail', label: '智慧零售', icon: 'ShoppingOutlined', color: '#1890ff' },
  { value: 'manufacturing', label: '智能制造', icon: 'ToolOutlined', color: '#722ed1' },
  { value: 'transport', label: '智慧交通', icon: 'CarOutlined', color: '#13c2c2' },
  { value: 'education', label: '智慧教育', icon: 'BookOutlined', color: '#eb2f96' },
  { value: 'energy', label: '能源环保', icon: 'ThunderboltOutlined', color: '#fa541c' },
  { value: 'agriculture', label: '智慧农业', icon: 'ExperimentOutlined', color: '#237804' },
  { value: 'other', label: '其他领域', icon: 'AppstoreOutlined', color: '#8c8c8c' },
];

// 隐私等级选项
export const mockPrivacyLevels = [
  {
    value: 'low',
    label: '低',
    description: '基础隐私保护，适合公开数据集',
    features: ['基础加密传输', '简单差分隐私'],
  },
  {
    value: 'medium',
    label: '中',
    description: '标准隐私保护，适合一般商业场景',
    features: ['TLS加密', '差分隐私(ε≤1)', '安全聚合'],
  },
  {
    value: 'high',
    label: '高',
    description: '高级隐私保护，适合敏感数据',
    features: ['端到端加密', '差分隐私(ε≤0.1)', '同态加密', '安全多方计算'],
  },
  {
    value: 'extreme',
    label: '极高',
    description: '最高级别保护，适合医疗、金融等高度敏感场景',
    features: ['全同态加密', '差分隐私(ε≤0.01)', '可信执行环境', '零知识证明'],
  },
];

// 预设模板
export const mockTaskTemplates = [
  {
    id: 'template-1',
    name: '医疗影像分类',
    category: 'healthcare',
    description: '适用于肺部CT、X光片等医疗影像的联邦学习分类任务',
    config: {
      modelType: 'ResNet50',
      optimizer: 'Adam',
      learningRate: 0.001,
      batchSize: 32,
      epochs: 5,
      aggregationStrategy: 'fedavg',
      targetAccuracy: 0.95,
      maxRounds: 100,
      dataFormats: ['DICOM', 'NIfTI', 'PNG'],
      minDataSize: 5000,
      minNodes: 3,
      maxNodes: 10,
      privacyLevel: 'high',
    },
  },
  {
    id: 'template-2',
    name: '金融风控预测',
    category: 'finance',
    description: '适用于银行、保险等金融机构的联合风控模型训练',
    config: {
      modelType: 'XGBoost',
      optimizer: 'Adam',
      learningRate: 0.01,
      batchSize: 256,
      epochs: 10,
      aggregationStrategy: 'fedprox',
      targetAccuracy: 0.92,
      maxRounds: 50,
      dataFormats: ['CSV', 'Parquet'],
      minDataSize: 10000,
      minNodes: 5,
      maxNodes: 20,
      privacyLevel: 'extreme',
    },
  },
  {
    id: 'template-3',
    name: '智能推荐系统',
    category: 'retail',
    description: '适用于电商、内容平台的联邦推荐模型',
    config: {
      modelType: 'DeepFM',
      optimizer: 'Adam',
      learningRate: 0.001,
      batchSize: 512,
      epochs: 3,
      aggregationStrategy: 'fedavg',
      targetAccuracy: 0.88,
      maxRounds: 80,
      dataFormats: ['CSV', 'JSON'],
      minDataSize: 50000,
      minNodes: 4,
      maxNodes: 15,
      privacyLevel: 'medium',
    },
  },
  {
    id: 'template-4',
    name: '语音识别模型',
    category: 'other',
    description: '适用于多方言、多场景的联邦语音模型训练',
    config: {
      modelType: 'Wave2Vec2',
      optimizer: 'AdamW',
      learningRate: 0.0001,
      batchSize: 16,
      epochs: 3,
      aggregationStrategy: 'scaffold',
      targetAccuracy: 0.9,
      maxRounds: 120,
      dataFormats: ['WAV', 'MP3'],
      minDataSize: 1000,
      minNodes: 6,
      maxNodes: 30,
      privacyLevel: 'medium',
    },
  },
];

// 预算建议
export const mockBudgetSuggestions = [
  { nodes: '3-5', rounds: '50', minBudget: 10000, recommendedBudget: 30000 },
  { nodes: '5-10', rounds: '100', minBudget: 50000, recommendedBudget: 100000 },
  { nodes: '10-20', rounds: '150', minBudget: 150000, recommendedBudget: 300000 },
  { nodes: '20+', rounds: '200', minBudget: 400000, recommendedBudget: 800000 },
];

// 默认表单数据
export const mockDefaultFormData = {
  // 基本信息
  name: '',
  description: '',
  category: '',
  tags: [],

  // 数据要求
  dataRequirements: {
    minDataSize: 5000,
    minNodes: 3,
    maxNodes: 10,
    dataFormats: ['CSV'],
    privacyLevel: 'medium',
  },

  // 训练配置
  trainingConfig: {
    modelType: 'ResNet50',
    optimizer: 'Adam',
    learningRate: 0.001,
    batchSize: 32,
    epochs: 5,
    aggregationStrategy: 'fedavg',
    targetAccuracy: 0.9,
    maxRounds: 100,
    timeoutPerRound: 300,
    differentialPrivacy: {
      enabled: true,
      epsilon: 1.0,
      delta: 0.0001,
    },
  },

  // 预算设置
  budget: {
    rewardPool: 50000,
    rewardCurrency: 'CNY',
    paymentMethod: 'prepaid',
    settlementCycle: 'per_round',
  },
};
