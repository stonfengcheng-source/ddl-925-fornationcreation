// 规则类型枚举
export type RuleType = 'format' | 'range' | 'logic' | 'custom';

// 规则状态
export type RuleStatus = 'draft' | 'active' | 'disabled';

// 字段定义
export interface FieldDefinition {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'date';
  description?: string;
}

// 测试用例
export interface TestCase {
  id: string;
  name: string;
  input: Record<string, unknown>;
  expectedResult: boolean;
  actualResult?: boolean;
  error?: string;
}

// 质量规则主接口
export interface QualityRule {
  id: string;
  name: string;
  description: string;        // 自然语言描述
  ruleType: RuleType;
  fieldDefinitions?: FieldDefinition[];
  generatedCode: string;      // 生成的 Python 代码
  codeExplanation?: string;   // 代码说明
  warnings?: string[];        // 警告信息
  testCases: TestCase[];
  status: RuleStatus;
  createdAt: string;
  updatedAt: string;
  createdBy?: string;
}

// 代码生成请求
export interface CodeGenerationRequest {
  naturalLanguage: string;
  ruleType: RuleType;
  fieldDefinitions?: FieldDefinition[];
}

// 代码生成响应
export interface CodeGenerationResponse {
  success: boolean;
  code: string;
  explanation: string;
  warnings?: string[];
}

// 代码测试请求
export interface CodeTestRequest {
  code: string;
  testData: Record<string, unknown>;
}

// 代码测试响应
export interface CodeTestResponse {
  success: boolean;
  result: boolean;
  error?: string;
  executionTime?: number;
}

// 规则表单数据（用于编辑器）
export interface RuleFormData {
  name: string;
  description: string;
  ruleType: RuleType;
  fieldDefinitions: FieldDefinition[];
}
