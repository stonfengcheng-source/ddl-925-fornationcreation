import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout, Row, Col, Spin, Breadcrumb, message } from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';

// 类型导入
import {
  QualityRule,
  RuleFormData,
  TestCase,
  RuleType,
} from '@/types/qualityRule';

// API 导入
import { qualityRuleApi } from '@/services/api/qualityRule';

// UI 组件导入
import { Button } from '@/components/ui/Button';

// 子组件导入
import NLRuleInput from './components/NLRuleInput';
import CodePreview from './components/CodePreview';
import TestPanel from './components/TestPanel';

const { Content } = Layout;

const QualityRuleEditor: React.FC = () => {
  const { ruleId } = useParams<{ ruleId: string }>();
  const navigate = useNavigate();
  const isEditMode = !!ruleId;

  // 加载状态
  const [loading, setLoading] = useState(isEditMode);
  const [generating, setGenerating] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // 表单状态
  const [ruleForm, setRuleForm] = useState<RuleFormData>({
    name: '',
    description: '',
    ruleType: 'range' as RuleType,
    fieldDefinitions: [],
  });

  // 生成的代码
  const [generatedCode, setGeneratedCode] = useState('');
  const [codeExplanation, setCodeExplanation] = useState('');
  const [warnings, setWarnings] = useState<string[]>([]);

  // 测试用例
  const [testCases, setTestCases] = useState<TestCase[]>([]);

  // 加载已有规则数据
  useEffect(() => {
    if (isEditMode && ruleId) {
      setLoading(true);
      qualityRuleApi
        .getRule(ruleId)
        .then((rule) => {
          setRuleForm({
            name: rule.name,
            description: rule.description,
            ruleType: rule.ruleType,
            fieldDefinitions: rule.fieldDefinitions || [],
          });
          setGeneratedCode(rule.generatedCode);
          setCodeExplanation(rule.codeExplanation || '');
          setWarnings(rule.warnings || []);
          setTestCases(rule.testCases);
        })
        .catch((err) => {
          message.error('加载规则失败：' + err.message);
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [isEditMode, ruleId]);

  // 生成代码
  const handleGenerateCode = async () => {
    if (!ruleForm.name || !ruleForm.description) {
      message.warning('请填写规则名称和描述');
      return;
    }

    setGenerating(true);
    try {
      const response = await qualityRuleApi.generateCode({
        naturalLanguage: ruleForm.description,
        ruleType: ruleForm.ruleType,
        fieldDefinitions: ruleForm.fieldDefinitions,
      });

      if (response.success) {
        setGeneratedCode(response.code);
        setCodeExplanation(response.explanation);
        setWarnings(response.warnings || []);
        message.success('代码生成成功');
      } else {
        message.error('代码生成失败');
      }
    } catch (err) {
      message.error('代码生成出错：' + (err as Error).message);
    } finally {
      setGenerating(false);
    }
  };

  // 添加测试用例
  const handleAddTestCase = (testCase: Omit<TestCase, 'id'>) => {
    const newTestCase: TestCase = {
      ...testCase,
      id: `TC-${Date.now()}`,
    };
    setTestCases((prev) => [...prev, newTestCase]);
    message.success('测试用例添加成功');
  };

  // 删除测试用例
  const handleDeleteTestCase = (testCaseId: string) => {
    setTestCases((prev) => prev.filter((tc) => tc.id !== testCaseId));
  };

  // 运行单个测试
  const handleRunTest = async (testCaseId: string) => {
    if (!generatedCode) {
      message.warning('请先生成验证代码');
      return;
    }

    const testCase = testCases.find((tc) => tc.id === testCaseId);
    if (!testCase) return;

    setTesting(testCaseId);
    try {
      const response = await qualityRuleApi.testCode({
        code: generatedCode,
        testData: testCase.input,
      });

      setTestCases((prev) =>
        prev.map((tc) =>
          tc.id === testCaseId
            ? {
                ...tc,
                actualResult: response.result,
                error: response.error,
              }
            : tc
        )
      );

      if (response.success) {
        message.success(
          `测试${response.result ? '通过' : '失败'}${
            response.executionTime ? ` (${response.executionTime}ms)` : ''
          }`
        );
      } else {
        message.error('测试执行失败：' + response.error);
      }
    } catch (err) {
      message.error('测试执行出错：' + (err as Error).message);
    } finally {
      setTesting(null);
    }
  };

  // 运行全部测试
  const handleRunAllTests = async () => {
    if (!generatedCode) {
      message.warning('请先生成验证代码');
      return;
    }

    if (testCases.length === 0) {
      message.warning('没有测试用例');
      return;
    }

    message.loading('正在运行所有测试...', 0);

    let passed = 0;
    let failed = 0;

    for (const testCase of testCases) {
      setTesting(testCase.id);
      try {
        const response = await qualityRuleApi.testCode({
          code: generatedCode,
          testData: testCase.input,
        });

        setTestCases((prev) =>
          prev.map((tc) =>
            tc.id === testCase.id
              ? {
                  ...tc,
                  actualResult: response.result,
                  error: response.error,
                }
              : tc
          )
        );

        if (response.result === testCase.expectedResult) {
          passed++;
        } else {
          failed++;
        }
      } catch (err) {
        failed++;
      }
    }

    setTesting(null);
    message.destroy();
    message.success(
      `测试完成：通过 ${passed} 个，失败 ${failed} 个`
    );
  };

  // 复制代码
  const handleCopyCode = () => {
    message.success('代码已复制到剪贴板');
  };

  // 保存规则
  const handleSave = async () => {
    if (!ruleForm.name || !ruleForm.description) {
      message.warning('请填写规则名称和描述');
      return;
    }

    if (!generatedCode) {
      message.warning('请先生成验证代码');
      return;
    }

    setSaving(true);
    try {
      const ruleData: Partial<QualityRule> = {
        ...ruleForm,
        generatedCode,
        codeExplanation,
        testCases,
        status: 'draft',
      };

      if (isEditMode && ruleId) {
        await qualityRuleApi.updateRule(ruleId, ruleData);
        message.success('规则更新成功');
      } else {
        const result = await qualityRuleApi.saveRule(ruleData);
        message.success('规则创建成功，ID: ' + result.id);
        navigate(`/app/quality-rules/editor/${result.id}`);
      }
    } catch (err) {
      message.error('保存失败：' + (err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  // 取消
  const handleCancel = () => {
    navigate(-1);
  };

  return (
    <Content className="p-6 bg-background min-h-screen">
      {/* 顶部标题栏 */}
      <div className="mb-6">
        <Breadcrumb
          items={[
            { title: '质量规则' },
            { title: isEditMode ? '编辑规则' : '新建规则' },
          ]}
          className="mb-4"
        />
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              onClick={handleCancel}
              className="flex items-center gap-2"
            >
              <ArrowLeftOutlined />
              返回
            </Button>
            <h1 className="text-2xl font-semibold text-text m-0">
              质量规则编辑器
            </h1>
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={handleCancel}>
              取消
            </Button>
            <Button
              variant="primary"
              effect="3d"
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2"
            >
              <SaveOutlined />
              {saving ? '保存中...' : '保存规则'}
            </Button>
          </div>
        </div>
      </div>

      {/* 三栏布局 */}
      {loading ? (
        <div className="flex justify-center items-center h-96">
          <Spin size="large" tip="加载中..." />
        </div>
      ) : (
        <Row gutter={24}>
          <Col xs={24} lg={8} className="mb-6 lg:mb-0">
            <div className="h-[calc(100vh-220px)]">
              <NLRuleInput
                value={ruleForm}
                onChange={setRuleForm}
                onGenerate={handleGenerateCode}
                loading={generating}
              />
            </div>
          </Col>
          <Col xs={24} lg={8} className="mb-6 lg:mb-0">
            <div className="h-[calc(100vh-220px)]">
              <CodePreview
                code={generatedCode}
                explanation={codeExplanation}
                warnings={warnings}
                loading={generating}
                onCopy={handleCopyCode}
                onRegenerate={handleGenerateCode}
              />
            </div>
          </Col>
          <Col xs={24} lg={8}>
            <div className="h-[calc(100vh-220px)]">
              <TestPanel
                testCases={testCases}
                onAddTestCase={handleAddTestCase}
                onRunTest={handleRunTest}
                onRunAllTests={handleRunAllTests}
                onDeleteTestCase={handleDeleteTestCase}
                runningTestId={testing}
              />
            </div>
          </Col>
        </Row>
      )}
    </Content>
  );
};

export default QualityRuleEditor;
