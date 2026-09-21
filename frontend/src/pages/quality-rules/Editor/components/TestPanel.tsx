import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { TestCase } from '@/types/qualityRule';
import { Plus, Trash2, Play, CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';

interface TestPanelProps {
  testCases: TestCase[];
  onAddTestCase: (testCase: Omit<TestCase, 'id'>) => void;
  onRunTest: (testCaseId: string) => void;
  onRunAllTests: () => void;
  onDeleteTestCase: (testCaseId: string) => void;
  runningTestId?: string | null;
}

export const TestPanel: React.FC<TestPanelProps> = ({
  testCases,
  onAddTestCase,
  onRunTest,
  onRunAllTests,
  onDeleteTestCase,
  runningTestId,
}) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTestName, setNewTestName] = useState('');
  const [newTestInput, setNewTestInput] = useState('{}');
  const [newTestExpected, setNewTestExpected] = useState(true);
  const [inputError, setInputError] = useState<string | null>(null);

  const handleAddTestCase = () => {
    try {
      const parsedInput = JSON.parse(newTestInput);
      onAddTestCase({
        name: newTestName || `测试用例 ${testCases.length + 1}`,
        input: parsedInput,
        expectedResult: newTestExpected,
      });
      setNewTestName('');
      setNewTestInput('{}');
      setNewTestExpected(true);
      setInputError(null);
      setShowAddForm(false);
    } catch (e) {
      setInputError('JSON 格式错误，请检查输入');
    }
  };

  const getStatusIcon = (testCase: TestCase) => {
    if (runningTestId === testCase.id) {
      return <Clock className="w-4 h-4 text-accent-blue animate-pulse" />;
    }
    if (testCase.actualResult === undefined) {
      return <AlertCircle className="w-4 h-4 text-text-placeholder" />;
    }
    if (testCase.actualResult === testCase.expectedResult) {
      return <CheckCircle className="w-4 h-4 text-[var(--accent-green)]" />;
    }
    return <XCircle className="w-4 h-4 text-[var(--accent-red)]" />;
  };

  const getStatusText = (testCase: TestCase) => {
    if (runningTestId === testCase.id) {
      return '运行中';
    }
    if (testCase.actualResult === undefined) {
      return '未测试';
    }
    if (testCase.actualResult === testCase.expectedResult) {
      return '通过';
    }
    return '失败';
  };

  const getStatusClass = (testCase: TestCase) => {
    if (runningTestId === testCase.id) {
      return 'bg-accent-blue/10 text-accent-blue';
    }
    if (testCase.actualResult === undefined) {
      return 'bg-background-tertiary text-text-secondary';
    }
    if (testCase.actualResult === testCase.expectedResult) {
      return 'bg-[var(--accent-green)] text-white';
    }
    return 'bg-[var(--accent-red)] text-white';
  };

  const passedCount = testCases.filter(
    (tc) => tc.actualResult !== undefined && tc.actualResult === tc.expectedResult
  ).length;
  const failedCount = testCases.filter(
    (tc) => tc.actualResult !== undefined && tc.actualResult !== tc.expectedResult
  ).length;
  const untestedCount = testCases.filter((tc) => tc.actualResult === undefined).length;

  return (
    <Card variant="neumorphic" className="h-full flex flex-col">
      <CardHeader className="flex flex-row justify-between items-center pb-2">
        <div>
          <CardTitle className="text-lg">测试验证</CardTitle>
          {testCases.length > 0 && (
            <div className="flex gap-3 mt-1 text-xs">
              <span className="text-[var(--accent-green)]">
                通过: {passedCount}
              </span>
              <span className="text-[var(--accent-red)]">
                失败: {failedCount}
              </span>
              <span className="text-text-secondary">
                未测试: {untestedCount}
              </span>
            </div>
          )}
        </div>
        <Button
          variant="primary"
          size="sm"
          onClick={onRunAllTests}
          disabled={testCases.length === 0 || !!runningTestId}
        >
          <Play className="w-4 h-4 mr-1" />
          全部运行
        </Button>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col space-y-4 overflow-auto">
        {/* 测试用例列表 */}
        <div className="space-y-2 flex-1">
          {testCases.length === 0 ? (
            <div className="text-center py-8 text-text-secondary">
              <AlertCircle className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>暂无测试用例</p>
              <p className="text-sm mt-1">点击下方按钮添加测试用例</p>
            </div>
          ) : (
            testCases.map((testCase) => (
              <Card
                key={testCase.id}
                variant="flat"
                className="p-3 overflow-hidden"
              >
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(testCase)}
                    <span className="text-sm font-medium">{testCase.name}</span>
                  </div>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${getStatusClass(
                      testCase
                    )}`}
                  >
                    {getStatusText(testCase)}
                  </span>
                </div>

                {/* 测试数据预览 */}
                <div className="mt-2 p-2 bg-white rounded text-xs font-mono text-text-secondary overflow-x-auto">
                  {JSON.stringify(testCase.input)}
                </div>

                {/* 期望结果 */}
                <div className="mt-2 text-xs text-text-secondary">
                  期望: {testCase.expectedResult ? '通过' : '失败'}
                  {testCase.actualResult !== undefined && (
                    <span className="ml-3">
                      实际: {testCase.actualResult ? '通过' : '失败'}
                    </span>
                  )}
                </div>

                {/* 错误信息 */}
                {testCase.error && (
                  <div className="mt-2 text-xs text-[var(--accent-red)] bg-[var(--accent-red)]/10 p-2 rounded">
                    {testCase.error}
                  </div>
                )}

                {/* 操作按钮 */}
                <div className="mt-3 flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onRunTest(testCase.id)}
                    disabled={runningTestId === testCase.id}
                  >
                    <Play className="w-3 h-3 mr-1" />
                    运行
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-[var(--accent-red)] hover:text-[var(--accent-red)]"
                    onClick={() => onDeleteTestCase(testCase.id)}
                  >
                    <Trash2 className="w-3 h-3 mr-1" />
                    删除
                  </Button>
                </div>
              </Card>
            ))
          )}
        </div>

        {/* 添加测试用例表单 */}
        {showAddForm ? (
          <Card variant="flat" className="p-4">
            <h4 className="text-sm font-medium mb-3">添加测试用例</h4>
            <div className="space-y-3">
              <Input
                placeholder="测试用例名称"
                value={newTestName}
                onChange={(e) => setNewTestName(e.target.value)}
              />
              <div>
                <label className="text-xs text-text-secondary mb-1 block">
                  测试数据 (JSON格式)
                </label>
                <textarea
                  className={`neumorphic-inset w-full h-24 p-2 rounded-md bg-white text-text text-sm font-mono resize-none ${
                    inputError ? 'border-[var(--accent-red)]' : ''
                  }`}
                  value={newTestInput}
                  onChange={(e) => {
                    setNewTestInput(e.target.value);
                    setInputError(null);
                  }}
                  placeholder='{"age": 25}'
                />
                {inputError && (
                  <p className="text-xs text-[var(--accent-red)] mt-1">{inputError}</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-text-secondary">期望结果:</label>
                <select
                  className="h-8 px-2 py-1 bg-white text-text text-sm border border-border-medium rounded-md neumorphic-inset"
                  value={newTestExpected.toString()}
                  onChange={(e) => setNewTestExpected(e.target.value === 'true')}
                >
                  <option value="true">通过</option>
                  <option value="false">失败</option>
                </select>
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => setShowAddForm(false)}>
                  取消
                </Button>
                <Button variant="primary" size="sm" onClick={handleAddTestCase}>
                  添加
                </Button>
              </div>
            </div>
          </Card>
        ) : (
          <Button variant="secondary" className="w-full" onClick={() => setShowAddForm(true)}>
            <Plus className="w-4 h-4 mr-2" />
            添加测试用例
          </Button>
        )}
      </CardContent>
    </Card>
  );
};

export default TestPanel;
