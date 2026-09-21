/**
 * TaskPublish 页面（简化版）
 * 任务发布向导 - 技术细节对用户透明
 *
 * 3步流程：
 * 1. 任务基本信息 - 名称、领域、描述
 * 2. 数据需求描述 - 需要什么数据
 * 3. 预算与确认 - 奖励设置、发布确认
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import request from '@/services/request';
import {
  Steps,
  Form,
  Input,
  Select,
  InputNumber,
  Button,
  Typography,
  Alert,
  Row,
  Col,
  Checkbox,
  Divider,
  Switch,
  Slider,
  Tooltip,
} from 'antd';
import {
  FileTextOutlined,
  DatabaseOutlined,
  DollarOutlined,
  CheckOutlined,
  MedicineBoxOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
  BarChartOutlined,
  ScanOutlined,
  ClusterOutlined,
  SafetyOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { Card as UICard } from '@/components/ui/Card';

const { TextArea } = Input;
const { Option } = Select;
const { Title, Text, Paragraph } = Typography;

// 科研领域选项
const domainOptions = [
  { value: 'medical-imaging', label: '医学影像', icon: <MedicineBoxOutlined />, color: '#1890ff', description: 'CT、MRI、X光、超声等医学影像分析' },
  { value: 'genomics', label: '基因组学', icon: <ExperimentOutlined />, color: '#722ed1', description: '基因序列、突变分析、表达谱等' },
  { value: 'clinical-research', label: '临床研究', icon: <FileTextOutlined />, color: '#52c41a', description: '病例分析、临床指标、随访数据等' },
  { value: 'pathology', label: '病理分析', icon: <DatabaseOutlined />, color: '#eb2f96', description: '病理切片、细胞学、组织学数据' },
  { value: 'drug-discovery', label: '药物研发', icon: <ThunderboltOutlined />, color: '#fa541c', description: '分子筛选、药效预测、临床试验' },
  { value: 'epidemiology', label: '流行病学', icon: <BarChartOutlined />, color: '#13c2c2', description: '疾病分布、风险因素、预后分析' },
  { value: 'radiomics', label: '影像组学', icon: <ScanOutlined />, color: '#faad14', description: '影像特征提取、定量分析、AI辅助诊断' },
  { value: 'multiomics', label: '多组学整合', icon: <ClusterOutlined />, color: '#237804', description: '基因组+影像+临床数据联合分析' },
];

// 科研数据类型选项
const dataTypeOptions = [
  { value: 'ct-scan', label: 'CT影像', desc: '计算机断层扫描图像' },
  { value: 'mri', label: 'MRI影像', desc: '磁共振成像' },
  { value: 'x-ray', label: 'X光影像', desc: 'X射线成像' },
  { value: 'ultrasound', label: '超声影像', desc: '超声波成像' },
  { value: 'pathology-slide', label: '病理切片', desc: '数字病理切片图像' },
  { value: 'genomic-sequence', label: '基因序列', desc: 'DNA/RNA测序数据' },
  { value: 'gene-expression', label: '基因表达', desc: '表达谱、转录组数据' },
  { value: 'mutation-data', label: '突变数据', desc: '基因突变、变异信息' },
  { value: 'clinical-record', label: '电子病历', desc: '结构化病历数据' },
  { value: 'lab-result', label: '检验结果', desc: '实验室检验指标' },
  { value: 'vital-signs', label: '生命体征', desc: '血压、心率、体温等' },
  { value: 'radiology-report', label: '影像报告', desc: '放射科诊断报告' },
  { value: 'pathology-report', label: '病理报告', desc: '病理诊断报告' },
  { value: 'demographics', label: '人口学数据', desc: '年龄、性别、病史等' },
  { value: 'follow-up', label: '随访数据', desc: '预后、复发、生存数据' },
];

// 结算周期选项
const settlementOptions = [
  { value: 'weekly', label: '每周结算' },
  { value: 'biweekly', label: '双周结算' },
  { value: 'monthly', label: '每月结算' },
  { value: 'per-round', label: '按轮次结算' },
  { value: 'on-completion', label: '任务完成结算' },
];

// 模型类型选项
const modelTypeOptions = [
  { value: 'breast_cancer', label: '乳腺癌诊断模型', desc: '三层全连接网络，用于乳腺癌二分类', taskType: 'classification' },
  { value: 'diabetes_mlp', label: '糖尿病预测(回归)', desc: 'MLP全连接网络，用于sklearn Diabetes回归预测', taskType: 'regression' },
];

interface FormData {
  name: string;
  domain: string;
  modelType: string;
  description: string;
  dataRequirements: {
    types: string[];
    minSamples: number;
    qualityScore: number;
    description: string;
  };
  budget: {
    totalReward: number;
    settlementCycle: string;
    targetAccuracy: number;
  };
  dpConfig: {
    enabled: boolean;
    epsilon: number;
    delta: number;
    noiseMultiplier: number;
    clippingNorm: number;
    adaptive: boolean;
  };
}

const defaultFormData: FormData = {
  name: '',
  domain: '',
  modelType: 'breast_cancer',
  description: '',
  dataRequirements: {
    types: [],
    minSamples: 1000,
    qualityScore: 80,
    description: '',
  },
  budget: {
    totalReward: 10000,
    settlementCycle: 'monthly',
    targetAccuracy: 85,
  },
  dpConfig: {
    enabled: false,
    epsilon: 1.0,
    delta: 1e-5,
    noiseMultiplier: 1.0,
    clippingNorm: 1.0,
    adaptive: false,
  },
};

const TaskPublish: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<FormData>(defaultFormData);
  const [submitting, setSubmitting] = useState(false);
  const [agreed, setAgreed] = useState(false);

  // 简化为3步
  const steps = [
    { title: '基本信息', icon: <FileTextOutlined />, description: '任务名称和领域' },
    { title: '数据需求', icon: <DatabaseOutlined />, description: '描述所需数据' },
    { title: '预算设置', icon: <DollarOutlined />, description: '奖励和结算方式' },
  ];

  // 下一步
  const handleNext = async () => {
    try {
      const values = await form.validateFields();
      setFormData((prev) => ({ ...prev, ...values }));
      setCurrentStep(currentStep + 1);
    } catch (error) {
      // 验证失败
    }
  };

  // 上一步
  const handlePrev = () => {
    setCurrentStep(currentStep - 1);
  };

  // 提交任务
  const handleSubmit = async () => {
    if (!agreed) return;
    setSubmitting(true);
    try {
      const payload = {
        task_name: formData.name,
        task_category: domainOptions.find(d => d.value === formData.domain)?.label || formData.domain || '其他',
        task_domain: formData.domain,
        task_description: formData.description,
        model_type: formData.modelType,
        data_requirements: {
          types: formData.dataRequirements.types,
          min_samples: formData.dataRequirements.minSamples,
          quality_score: formData.dataRequirements.qualityScore,
          description: formData.dataRequirements.description,
        },
        budget: {
          total_reward: formData.budget.totalReward,
          settlement_cycle: formData.budget.settlementCycle,
          target_accuracy: formData.budget.targetAccuracy,
        },
        dp_config: formData.dpConfig.enabled ? {
          enabled: true,
          epsilon: formData.dpConfig.epsilon,
          delta: formData.dpConfig.delta,
          noise_multiplier: formData.dpConfig.noiseMultiplier,
          clipping_norm: formData.dpConfig.clippingNorm,
          adaptive: formData.dpConfig.adaptive,
        } : undefined,
      };
      await request.post('/tasks', payload);
      const { message } = await import('antd');
      message.success('任务发布成功！');
      navigate('/app/tasks');
    } catch (error: any) {
      console.error('发布失败:', error);
      const { message } = await import('antd');
      const detail = error?.response?.data?.detail || error?.response?.data?.error?.message || '发布失败，请重试';
      message.error(detail);
    } finally {
      setSubmitting(false);
    }
  };

  // 渲染步骤内容
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-6">
            <Alert
              message="联邦学习流程说明"
              description="系统将自动匹配符合条件的数据提供方，在各方数据不出域的前提下完成联合建模。您只需描述任务需求和数据要求，技术细节由系统自动处理。"
              type="info"
              showIcon
            />

            <Form
              form={form}
              layout="vertical"
              initialValues={formData}
              requiredMark={false}
            >
              <Form.Item
                name="name"
                label="任务名称"
                rules={[{ required: true, message: '请输入任务名称' }]}
              >
                <Input placeholder="例如：肺癌早期诊断模型联合训练" />
              </Form.Item>

              <Form.Item
                name="domain"
                label="任务领域"
                rules={[{ required: true, message: '请选择任务领域' }]}
              >
                <Select placeholder="选择任务所属领域">
                  {domainOptions.map((opt) => (
                    <Option key={opt.value} value={opt.value}>
                      <div className="flex items-center gap-2">
                        <span style={{ color: opt.color }}>{opt.icon}</span>
                        <span>{opt.label}</span>
                        <span className="text-gray-400 text-sm">- {opt.description}</span>
                      </div>
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                name="modelType"
                label="模型类型"
                rules={[{ required: true, message: '请选择模型类型' }]}
              >
                <Select placeholder="选择联邦学习模型">
                  {modelTypeOptions.map((opt) => (
                    <Option key={opt.value} value={opt.value}>
                      <div>
                        <div className="font-medium">{opt.label}</div>
                        <div className="text-xs text-gray-400">{opt.desc} [{opt.taskType === 'regression' ? '回归' : '分类'}]</div>
                      </div>
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                name="description"
                label="任务描述"
                rules={[{ required: true, message: '请输入任务描述' }]}
              >
                <TextArea
                  rows={4}
                  placeholder="详细描述任务目标、预期成果、应用场景等"
                />
              </Form.Item>
            </Form>
          </div>
        );

      case 1:
        return (
          <div className="space-y-6">
            <Form
              form={form}
              layout="vertical"
              initialValues={formData}
              requiredMark={false}
            >
              <Form.Item
                name={['dataRequirements', 'types']}
                label="需要的数据类型"
                rules={[{ required: true, message: '请至少选择一种数据类型' }]}
              >
                <Select mode="multiple" placeholder="选择需要的数据类型">
                  {dataTypeOptions.map((opt) => (
                    <Option key={opt.value} value={opt.value}>
                      <div>
                        <div>{opt.label}</div>
                        <div className="text-xs text-gray-400">{opt.desc}</div>
                      </div>
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name={['dataRequirements', 'minSamples']}
                    label="最少样本量"
                    rules={[{ required: true }]}
                  >
                    <InputNumber
                      min={100}
                      step={100}
                      style={{ width: '100%' }}
                      placeholder="例如：1000"
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name={['dataRequirements', 'qualityScore']}
                    label="最低质量分"
                    rules={[{ required: true }]}
                  >
                    <InputNumber
                      min={0}
                      max={100}
                      style={{ width: '100%' }}
                      placeholder="0-100"
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name={['dataRequirements', 'description']}
                label="数据需求补充说明"
              >
                <TextArea
                  rows={3}
                  placeholder="例如：需要包含基因突变信息、年龄范围18-65岁、确诊时间在2020年后等"
                />
              </Form.Item>

              <Form.Item label="绑定质量规则">
                <Select placeholder="选择适用的质量验证规则（可选）" allowClear>
                  <Option value="rule-1">医疗数据基础质量规则</Option>
                  <Option value="rule-2">基因数据完整性检查</Option>
                  <Option value="rule-3">影像数据标准化规则</Option>
                </Select>
              </Form.Item>
            </Form>
          </div>
        );

      case 2:
        return (
          <div className="space-y-6">
            <Form
              form={form}
              layout="vertical"
              initialValues={formData}
              requiredMark={false}
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name={['budget', 'totalReward']}
                    label="总奖励金额"
                    rules={[{ required: true }]}
                  >
                    <InputNumber
                      min={1000}
                      step={1000}
                      style={{ width: '100%' }}
                      prefix="¥"
                      placeholder="10000"
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name={['budget', 'settlementCycle']}
                    label="结算周期"
                    rules={[{ required: true }]}
                  >
                    <Select placeholder="选择结算周期">
                      {settlementOptions.map((opt) => (
                        <Option key={opt.value} value={opt.value}>
                          {opt.label}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name={['budget', 'targetAccuracy']}
                label="目标准确率（%）"
                rules={[{ required: true }]}
              >
                <InputNumber
                  min={50}
                  max={100}
                  style={{ width: '100%' }}
                  placeholder="例如：85"
                />
              </Form.Item>
            </Form>

            {/* 差分隐私配置 */}
            <UICard variant="default" className="p-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <SafetyOutlined className="text-orange-500 text-lg" />
                  <Title level={5} style={{ margin: 0 }}>差分隐私保护</Title>
                  <Tooltip title="差分隐私通过在模型参数中添加受控噪声，防止训练数据被反向推断，保护数据提供方的隐私安全。启用后会略微降低模型精度，但能提供数学可证明的隐私保障。">
                    <QuestionCircleOutlined className="text-gray-400" />
                  </Tooltip>
                </div>
                <Switch
                  checked={formData.dpConfig.enabled}
                  onChange={(checked) => setFormData(prev => ({
                    ...prev,
                    dpConfig: { ...prev.dpConfig, enabled: checked },
                  }))}
                  checkedChildren="已启用"
                  unCheckedChildren="未启用"
                />
              </div>

              {formData.dpConfig.enabled && (
                <div className="space-y-4">
                  <Alert
                    message="差分隐私已启用"
                    description="系统将在联邦聚合时对模型参数添加噪声，保护各节点数据隐私。噪声越大隐私保护越强，但模型精度可能下降。"
                    type="info"
                    showIcon
                    className="mb-4"
                  />
                  <Row gutter={16}>
                    <Col span={12}>
                      <div className="mb-2">
                        <Text strong>隐私预算 ε</Text>
                        <Tooltip title="ε 越小隐私保护越强。典型值：0.1（极强）、1.0（中等）、10.0（弱）">
                          <QuestionCircleOutlined className="ml-1 text-gray-400" />
                        </Tooltip>
                      </div>
                      <Slider
                        min={0.1}
                        max={10}
                        step={0.1}
                        value={formData.dpConfig.epsilon}
                        onChange={(val) => setFormData(prev => ({
                          ...prev,
                          dpConfig: { ...prev.dpConfig, epsilon: val },
                        }))}
                      />
                      <InputNumber
                        min={0.01}
                        max={100}
                        step={0.1}
                        value={formData.dpConfig.epsilon}
                        onChange={(val) => val && setFormData(prev => ({
                          ...prev,
                          dpConfig: { ...prev.dpConfig, epsilon: val },
                        }))}
                        style={{ width: '100%' }}
                        addonAfter="ε"
                      />
                    </Col>
                    <Col span={12}>
                      <div className="mb-2">
                        <Text strong>噪声倍数</Text>
                        <Tooltip title="控制添加噪声的强度。值越大噪声越多，隐私保护越强，但精度下降越多。推荐 0.5-2.0">
                          <QuestionCircleOutlined className="ml-1 text-gray-400" />
                        </Tooltip>
                      </div>
                      <Slider
                        min={0.1}
                        max={5}
                        step={0.1}
                        value={formData.dpConfig.noiseMultiplier}
                        onChange={(val) => setFormData(prev => ({
                          ...prev,
                          dpConfig: { ...prev.dpConfig, noiseMultiplier: val },
                        }))}
                      />
                      <InputNumber
                        min={0.01}
                        max={10}
                        step={0.1}
                        value={formData.dpConfig.noiseMultiplier}
                        onChange={(val) => val && setFormData(prev => ({
                          ...prev,
                          dpConfig: { ...prev.dpConfig, noiseMultiplier: val },
                        }))}
                        style={{ width: '100%' }}
                      />
                    </Col>
                  </Row>
                  <Row gutter={16}>
                    <Col span={12}>
                      <div className="mb-2">
                        <Text strong>裁剪范数</Text>
                        <Tooltip title="限制每个客户端模型更新的最大幅度。推荐 0.5-5.0">
                          <QuestionCircleOutlined className="ml-1 text-gray-400" />
                        </Tooltip>
                      </div>
                      <InputNumber
                        min={0.01}
                        max={50}
                        step={0.1}
                        value={formData.dpConfig.clippingNorm}
                        onChange={(val) => val && setFormData(prev => ({
                          ...prev,
                          dpConfig: { ...prev.dpConfig, clippingNorm: val },
                        }))}
                        style={{ width: '100%' }}
                      />
                    </Col>
                    <Col span={12}>
                      <div className="mb-2">
                        <Text strong>裁剪模式</Text>
                        <Tooltip title="固定裁剪使用固定范数值；自适应裁剪会根据训练情况自动调整裁剪范数">
                          <QuestionCircleOutlined className="ml-1 text-gray-400" />
                        </Tooltip>
                      </div>
                      <Select
                        value={formData.dpConfig.adaptive ? 'adaptive' : 'fixed'}
                        onChange={(val) => setFormData(prev => ({
                          ...prev,
                          dpConfig: { ...prev.dpConfig, adaptive: val === 'adaptive' },
                        }))}
                        style={{ width: '100%' }}
                      >
                        <Option value="fixed">固定裁剪</Option>
                        <Option value="adaptive">自适应裁剪</Option>
                      </Select>
                    </Col>
                  </Row>
                </div>
              )}
            </UICard>

            <Divider />

            {/* 发布确认 */}
            <UICard variant="default" className="p-4">
              <Title level={5}>发布确认</Title>

              <div className="mt-4 space-y-3">
                <div className="flex justify-between">
                  <Text type="secondary">任务名称</Text>
                  <Text strong>{formData.name || '-'}</Text>
                </div>
                <div className="flex justify-between">
                  <Text type="secondary">任务领域</Text>
                  <Text>
                    {domainOptions.find(d => d.value === formData.domain)?.label || '-'}
                  </Text>
                </div>
                <div className="flex justify-between">
                  <Text type="secondary">模型类型</Text>
                  <Text>
                    {modelTypeOptions.find(m => m.value === formData.modelType)?.label || '-'}
                  </Text>
                </div>
                <div className="flex justify-between">
                  <Text type="secondary">数据类型</Text>
                  <Text>
                    {formData.dataRequirements.types?.length
                      ? `${formData.dataRequirements.types.length} 种`
                      : '-'}
                  </Text>
                </div>
                <div className="flex justify-between">
                  <Text type="secondary">最少样本</Text>
                  <Text>{formData.dataRequirements.minSamples?.toLocaleString() || '-'} 例</Text>
                </div>
                <div className="flex justify-between">
                  <Text type="secondary">总奖励</Text>
                  <Text strong className="text-green-600">
                    ¥{formData.budget.totalReward?.toLocaleString() || '-'}
                  </Text>
                </div>
                <div className="flex justify-between">
                  <Text type="secondary">差分隐私</Text>
                  <Text style={{ color: formData.dpConfig.enabled ? '#fa8c16' : '#8c8c8c' }}>
                    {formData.dpConfig.enabled
                      ? `已启用 (ε=${formData.dpConfig.epsilon}, 噪声=${formData.dpConfig.noiseMultiplier})`
                      : '未启用'}
                  </Text>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t">
                <Checkbox
                  checked={agreed}
                  onChange={(e) => setAgreed(e.target.checked)}
                >
                  我已阅读并同意
                  <a href="#" onClick={(e) => e.preventDefault()}>《联邦学习任务协议》</a>
                </Checkbox>
              </div>
            </UICard>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-8">
      <Title level={3}>发布联邦学习任务</Title>
      <Paragraph type="secondary" className="mb-6">
        描述您的任务需求，系统将自动匹配符合条件的数据提供方
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
          disabled={currentStep === 0}
        >
          上一步
        </Button>

        {currentStep < steps.length - 1 ? (
          <Button type="primary" onClick={handleNext}>
            下一步
          </Button>
        ) : (
          <Button
            type="primary"
            onClick={handleSubmit}
            loading={submitting}
            disabled={!agreed}
            icon={<CheckOutlined />}
          >
            发布任务
          </Button>
        )}
      </div>
    </div>
  );
};

export default TaskPublish;
