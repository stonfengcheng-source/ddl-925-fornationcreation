export interface QualityReport {
  dataId: string;
  overallScore: number;
  rating: 'excellent' | 'good' | 'fair' | 'poor';
  layerScores: {
    layer1: number;
    layer2: number;
    layer3: number;
    layer4: number;
    layer5: number;
  };
  suitableScenarios: string[];
  unsuitableScenarios: string[];
  diagnosticDetails: {
    layer1: Layer1Details;
    layer2: Layer2Details;
    layer3: Layer3Details;
    layer4: Layer4Details;
  };
  recommendations: string[];
  generatedAt: string;
}

export interface Layer1Details {
  sampleSize: number;
  missingRate: number;
  outlierRate: number;
  featureStats: Array<{
    name: string;
    mean: number;
    std: number;
    min: number;
    max: number;
  }>;
}

export interface Layer2Details {
  correlationMatrix: number[][];
  significantPairs: Array<{
    feature1: string;
    feature2: string;
    correlation: number;
    pValue: number;
  }>;
  featureNames?: string[]; // 为了热力图轴标签，可选，若不传则可能需要硬编码或从其他地方获取
}

export interface Layer3Details {
  distributionFits: Array<{
    feature: string;
    bestFit: string;
    pValue: number;
    isNormal: boolean;
  }>;
}

export interface Layer4Details {
  interactionEffects: Array<{
    features: [string, string];
    strength: number;
    type: 'synergy' | 'redundancy';
  }>;
}
