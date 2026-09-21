import { QualityReport } from '../types/quality';

export const mockQualityReport: QualityReport = {
  dataId: 'DATA-001',
  overallScore: 78,
  rating: 'good',
  layerScores: {
    layer1: 92,
    layer2: 85,
    layer3: 80,
    layer4: 45,
    layer5: 0
  },
  suitableScenarios: ['回归预测', '分类任务', '时序分析'],
  unsuitableScenarios: ['异常检测', '因果推断'],
  recommendations: [
    '数据质量良好，适合用于模型训练',
    'Layer 4 得分较低，建议补充高阶交互特征',
    '特征分布较为平稳，无需大量预处理'
  ],
  generatedAt: '2023-10-27T10:00:00Z',
  diagnosticDetails: {
    layer1: {
      sampleSize: 5000,
      missingRate: 0.02,
      outlierRate: 0.01,
      featureStats: [
        { name: 'Age', mean: 35.4, std: 12.1, min: 18, max: 85 },
        { name: 'BMI', mean: 24.5, std: 4.2, min: 16, max: 40 },
        { name: 'BP', mean: 120, std: 15, min: 90, max: 180 }
      ]
    },
    layer2: {
      featureNames: ['Age', 'BMI', 'BP'],
      correlationMatrix: [
        [1.0, 0.45, 0.60],
        [0.45, 1.0, 0.30],
        [0.60, 0.30, 1.0]
      ],
      significantPairs: [
        { feature1: 'Age', feature2: 'BP', correlation: 0.60, pValue: 0.001 },
        { feature1: 'Age', feature2: 'BMI', correlation: 0.45, pValue: 0.02 }
      ]
    },
    layer3: {
      distributionFits: [
        { feature: 'Age', bestFit: 'Normal', pValue: 0.08, isNormal: true },
        { feature: 'BMI', bestFit: 'Log-Normal', pValue: 0.01, isNormal: false }
      ]
    },
    layer4: {
      interactionEffects: [
        { features: ['Age', 'BMI'], strength: 0.35, type: 'synergy' },
        { features: ['BP', 'BMI'], strength: 0.12, type: 'redundancy' }
      ]
    }
  }
};
