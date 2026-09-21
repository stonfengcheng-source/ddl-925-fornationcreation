/**
 * 数据画像登记向导
 * 替代旧的数据集上传，实现数据不出域
 *
 * 3步流程：
 * 1. 选择本地数据文件（仅选择路径，不上传）
 * 2. 自动分析（本地Mock）生成数据画像
 * 3. 确认发布（只上传画像元数据，不传输原始数据）
 */

import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Steps,
  Button,
  Input,
  Form,
  Select,
  Tag,
  Progress,
  Alert,
  Row,
  Col,
  Statistic,
  Empty,
  message,
  Typography,
  Divider,
} from 'antd';
import {
  FileOutlined,
  CheckCircleOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
  LoadingOutlined,
  CheckOutlined,
  BarChartOutlined,
  HddOutlined,
} from '@ant-design/icons';
import { Card as UICard } from '@/components/ui/Card';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

// 步骤枚举
enum ProfileStep {
  SELECT_FILE = 0,
  ANALYZE = 1,
  PUBLISH = 2,
}

// 数据画像接口
interface DataProfile {
  name: string;
  localPath: string;
  description?: string;
  schema: {
    sampleCount: number;
    featureCount: number;
    numericFeatures: string[];
    categoricalFeatures: string[];
    missingRate: number;
  };
  domainTags: {
    primary: string;
    secondary: string[];
    dataType: string;
  };
  quality: {
    score: number;
    issues: string[];
  };
  capabilities: {
    taskTypes: string[];
    expectedAccuracy: { min: number; max: number };
  };
}

// Mock 分析结果
const mockAnalysisResult: DataProfile = {
  name: '',
  localPath: '',
  schema: {
    sampleCount: 5000,
    featureCount: 128,
    numericFeatures: ['age', 'blood_pressure_systolic', 'blood_pressure_diastolic', 'heart_rate', 'bmi'],
    categoricalFeatures: ['gender', 'smoking_status', 'family_history'],
    missingRate: 0.02,
  },
  domainTags: {
    primary: 'medical',
    secondary: ['oncology', 'radiology'],
    dataType: 'CT-scan',
  },
  quality: {
    score: 0.87,
    issues: ['minor_missing_values', 'class_imbalance'],
  },
  capabilities: {
    taskTypes: ['binary-classification', 'survival-analysis', 'risk-prediction'],
    expectedAccuracy: { min: 0.82, max: 0.91 },
  },
};

// 数据类型选项
const dataTypeOptions = [
  { value: 'medical', label: '医疗数据', color: 'red' },
  { value: 'genomic', label: '基因数据', color: 'purple' },
  { value: 'image', label: '影像数据', color: 'blue' },
  { value: 'finance', label: '金融数据', color: 'green' },
  { value: 'text', label: '文本数据', color: 'orange' },
];

const DataProfileCreate: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<ProfileStep>(ProfileStep.SELECT_FILE);
  const [form] = Form.useForm();
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [profile, setProfile] = useState<DataProfile | null>(null);
  const [publishing, setPublishing] = useState(false);

  // 步骤标题
  const steps = [
    { title: '选择数据', icon: <FileOutlined /> },
    { title: '自动分析', icon: <BarChartOutlined /> },
    { title: '发布画像', icon: <CheckCircleOutlined /> },
  ];

  // 下一步
  const handleNext = async () => {
    try {
      if (currentStep === ProfileStep.SELECT_FILE) {
        const values = await form.validateFields();
        // 进入分析步骤
        setCurrentStep(ProfileStep.ANALYZE);
        startAnalysis(values);
      } else if (currentStep === ProfileStep.ANALYZE) {
        setCurrentStep(ProfileStep.PUBLISH);
      } else if (currentStep === ProfileStep.PUBLISH) {
        handlePublish();
      }
    } catch (error) {
      // 验证失败
    }
  };

  // 上一步
  const handlePrev = () => {
    setCurrentStep(currentStep - 1);
  };

  // 开始分析（Mock）
  const startAnalysis = useCallback((formValues: any) => {
    setAnalyzing(true);
    setAnalysisProgress(0);

    // 模拟分析进度
    const interval = setInterval(() => {
      setAnalysisProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setAnalyzing(false);
          // 生成分析结果
          setProfile({
            ...mockAnalysisResult,
            name: formValues.name,
            localPath: formValues.localPath,
            description: formValues.description,
          });
          return 100;
        }
        return prev + 10;
      });
    }, 300);
  }, []);

  // 发布画像 — 调用真实后端 API
  const handlePublish = async () => {
    if (!profile) return;
    setPublishing(true);
    try {
      const request = (await import('@/services/request')).default;
      await request.post('/datasets', {
        name: profile.name,
        description: profile.description || '',
        data_type: profile.domainTags.dataType || 'csv',
        row_count: profile.schema.sampleCount,
        column_count: profile.schema.featureCount,
        tags: [profile.domainTags.primary, ...profile.domainTags.secondary],
        quality_score: profile.quality.score,
        columns_info: [
          ...profile.schema.numericFeatures.map(f => ({ name: f, type: 'numeric' })),
          ...profile.schema.categoricalFeatures.map(f => ({ name: f, type: 'categorical' })),
        ],
      });
      message.success('数据画像发布成功！原始数据仍保存在您的本地节点。');
      navigate('/app/data-assets');
    } catch (error: any) {
      console.error('发布失败:', error);
      const detail = error?.response?.data?.detail || error?.response?.data?.error?.message || '发布失败，请重试';
      message.error(detail);
    } finally {
      setPublishing(false);
    }
  };

  // 渲染步骤内容
  const renderStepContent = () => {
    switch (currentStep) {
      case ProfileStep.SELECT_FILE:
        return (
          <div className="space-y-6">
            <Alert
              message="数据不出域保护"
              description="我们只分析数据的特征画像，不会上传您的原始数据。原始数据始终保留在您的本地节点。"
              type="info"
              showIcon
            />

            <UICard variant="default" className="p-6">
              <Form
                form={form}
                layout="vertical"
                requiredMark={false}
              >
                <Form.Item
                  name="name"
                  label="数据名称"
                  rules={[{ required: true, message: '请输入数据名称' }]}
                >
                  <Input placeholder="例如：北京协和医院-肺癌CT影像数据" />
                </Form.Item>

                <Form.Item
                  name="localPath"
                  label="本地数据路径"
                  rules={[{ required: true, message: '请输入本地数据路径' }]}
                >
                  <Input
                    placeholder="例如：/data/medical/lung_cancer_2024.csv"
                    prefix={<HddOutlined />}
                  />
                </Form.Item>

                <Form.Item
                  name="dataType"
                  label="数据类型"
                  rules={[{ required: true, message: '请选择数据类型' }]}
                >
                  <Select placeholder="选择数据类型">
                    {dataTypeOptions.map((opt) => (
                      <Option key={opt.value} value={opt.value}>
                        <Tag color={opt.color}>{opt.label}</Tag>
                      </Option>
                    ))}
                  </Select>
                </Form.Item>

                <Form.Item name="description" label="数据描述">
                  <TextArea
                    rows={4}
                    placeholder="描述数据的来源、采集时间、特殊说明等（可选）"
                  />
                </Form.Item>

                <Form.Item
                  name="nodeId"
                  label="关联边缘节点"
                  rules={[{ required: true, message: '请选择关联节点' }]}
                >
                  <Select placeholder="选择存储此数据的边缘节点">
                    <Option value="node-1">节点-1 (本地服务器)</Option>
                    <Option value="node-2">节点-2 (实验室)</Option>
                  </Select>
                </Form.Item>
              </Form>
            </UICard>
          </div>
        );

      case ProfileStep.ANALYZE:
        return (
          <div className="space-y-6">
            {analyzing ? (
              <UICard variant="default" className="p-8 text-center">
                <LoadingOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                <Title level={4} className="mt-4">正在分析数据特征...</Title>
                <Text type="secondary">在本地节点执行，不会上传原始数据</Text>
                <Progress
                  percent={analysisProgress}
                  status="active"
                  className="mt-4"
                />
              </UICard>
            ) : profile ? (
              <div className="space-y-4">
                <Alert
                  message="分析完成"
                  description="已生成数据画像，点击下方按钮进入发布步骤"
                  type="success"
                  showIcon
                />

                {/* 数据概览 */}
                <UICard variant="default" className="p-6">
                  <Title level={5}>数据概览</Title>
                  <Row gutter={16} className="mt-4">
                    <Col span={8}>
                      <Statistic
                        title="样本量"
                        value={profile.schema.sampleCount}
                        suffix="例"
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="特征维度"
                        value={profile.schema.featureCount}
                        suffix="维"
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="质量评分"
                        value={Math.round(profile.quality.score * 100)}
                        suffix="分"
                      />
                    </Col>
                  </Row>
                </UICard>

                {/* 领域识别 */}
                <UICard variant="default" className="p-6">
                  <Title level={5}>领域识别</Title>
                  <div className="mt-4">
                    <Text strong>主要领域：</Text>
                    <Tag color="red" className="ml-2">医疗数据</Tag>
                  </div>
                  <div className="mt-2">
                    <Text strong>细分标签：</Text>
                    {profile.domainTags.secondary.map((tag) => (
                      <Tag key={tag} className="ml-2">{tag}</Tag>
                    ))}
                  </div>
                  <div className="mt-2">
                    <Text strong>数据类型：</Text>
                    <Tag color="blue" className="ml-2">{profile.domainTags.dataType}</Tag>
                  </div>
                </UICard>

                {/* 适用任务 */}
                <UICard variant="default" className="p-6">
                  <Title level={5}>适用任务类型</Title>
                  <div className="mt-4 space-x-2">
                    {profile.capabilities.taskTypes.map((task) => (
                      <Tag key={task} color="green">
                        {task === 'binary-classification' && '二分类'}
                        {task === 'survival-analysis' && '生存分析'}
                        {task === 'risk-prediction' && '风险预测'}
                      </Tag>
                    ))}
                  </div>
                  <div className="mt-4">
                    <Text type="secondary">
                      预计准确率范围：{(profile.capabilities.expectedAccuracy.min * 100).toFixed(0)}% - {(profile.capabilities.expectedAccuracy.max * 100).toFixed(0)}%
                    </Text>
                  </div>
                </UICard>

                {/* Schema 预览 */}
                <UICard variant="default" className="p-6">
                  <Title level={5}>字段结构预览</Title>
                  <div className="mt-4">
                    <Text strong>数值字段（{profile.schema.numericFeatures.length}个）：</Text>
                    <div className="mt-2">
                      {profile.schema.numericFeatures.map((f) => (
                        <Tag key={f}>{f}</Tag>
                      ))}
                    </div>
                  </div>
                  <div className="mt-4">
                    <Text strong>类别字段（{profile.schema.categoricalFeatures.length}个）：</Text>
                    <div className="mt-2">
                      {profile.schema.categoricalFeatures.map((f) => (
                        <Tag key={f}>{f}</Tag>
                      ))}
                    </div>
                  </div>
                </UICard>
              </div>
            ) : (
              <Empty description="分析失败，请返回重试" />
            )}
          </div>
        );

      case ProfileStep.PUBLISH:
        return (
          <div className="space-y-6">
            <UICard variant="default" className="p-6">
              <Title level={5}>发布确认</Title>
              <Alert
                className="mt-4"
                message="即将上传的内容"
                description={
                  <ul className="list-disc pl-4 mt-2 space-y-1">
                    <li>数据画像（统计特征、领域标签、适用任务）</li>
                    <li>数据质量评估结果</li>
                    <li>字段结构描述（仅名称和类型）</li>
                  </ul>
                }
                type="info"
                showIcon
              />
              <Alert
                className="mt-4"
                message="不会上传的内容"
                description={
                  <ul className="list-disc pl-4 mt-2 space-y-1">
                    <li>原始数据文件</li>
                    <li>具体数据值</li>
                    <li>个人隐私信息</li>
                  </ul>
                }
                type="success"
                showIcon
              />
            </UICard>

            {profile && (
              <UICard variant="default" className="p-6">
                <Title level={5}>数据资产预览</Title>
                <Divider />
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Text type="secondary">数据名称</Text>
                    <div className="font-medium">{profile.name}</div>
                  </Col>
                  <Col span={12}>
                    <Text type="secondary">本地路径</Text>
                    <div className="font-medium">{profile.localPath}</div>
                  </Col>
                  <Col span={12}>
                    <Text type="secondary">规模</Text>
                    <div className="font-medium">
                      {profile.schema.sampleCount.toLocaleString()} 样本 × {profile.schema.featureCount} 特征
                    </div>
                  </Col>
                  <Col span={12}>
                    <Text type="secondary">质量评分</Text>
                    <div className="font-medium">
                      {Math.round(profile.quality.score * 100)} 分
                    </div>
                  </Col>
                </Row>
              </UICard>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8">
      <Title level={3}>登记数据资产</Title>
      <Paragraph type="secondary" className="mb-6">
        通过自动分析生成数据画像，在不出域的前提下参与联邦学习任务
      </Paragraph>

      <Steps
        current={currentStep}
        items={steps}
        className="mb-8"
      />

      {renderStepContent()}

      <div className="flex justify-between mt-8">
        <Button
          onClick={handlePrev}
          disabled={currentStep === ProfileStep.SELECT_FILE}
          icon={<ArrowLeftOutlined />}
        >
          上一步
        </Button>

        {currentStep === ProfileStep.ANALYZE && analyzing ? (
          <Button type="primary" disabled>
            分析中...
          </Button>
        ) : (
          <Button
            type="primary"
            onClick={handleNext}
            loading={publishing}
            icon={currentStep === ProfileStep.PUBLISH ? <CheckOutlined /> : <ArrowRightOutlined />}
          >
            {currentStep === ProfileStep.PUBLISH ? '确认发布' : '下一步'}
          </Button>
        )}
      </div>
    </div>
  );
};

export default DataProfileCreate;
