// @ts-ignore - request 预留用于后续真实 API 调用
import request from '@/services/request';
import {
  QualityRule,
  CodeGenerationRequest,
  CodeGenerationResponse,
  CodeTestRequest,
  CodeTestResponse,
} from '@/types/qualityRule';

// Mock 延迟函数
const mockDelay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Mock 数据导入（开发阶段使用）
import {
  mockQualityRules,
  mockCodeGenerationResponse,
  mockCodeTestSuccess,
  mockCodeTestFailure,
} from '@/mocks/qualityRuleMock';

/**
 * 质量规则 API 服务
 */
export const qualityRuleApi = {
  /**
   * 获取规则列表
   */
  async getRules(): Promise<QualityRule[]> {
    // TODO: 替换为真实 API
    // return request.get<QualityRule[]>('/quality-rules');
    await mockDelay(500);
    return mockQualityRules;
  },

  /**
   * 获取单个规则
   * @param id - 规则 ID
   */
  async getRule(id: string): Promise<QualityRule> {
    // TODO: 替换为真实 API
    // return request.get<QualityRule>(`/quality-rules/${id}`);
    await mockDelay(300);
    const rule = mockQualityRules.find((r) => r.id === id);
    if (!rule) throw new Error('规则不存在');
    return rule;
  },

  /**
   * 生成验证代码
   * @param data - 代码生成请求参数
   */
  async generateCode(data: CodeGenerationRequest): Promise<CodeGenerationResponse> {
    // TODO: 替换为真实 API 调用 KIMI K2.5
    // return request.post<CodeGenerationResponse>('/quality-rules/generate', data);
    await mockDelay(1500); // 模拟 AI 生成延迟
    return {
      ...mockCodeGenerationResponse,
      code: `def validate(data):\n    """\n    ${data.naturalLanguage}\n    """\n    # TODO: 实现验证逻辑\n    return True, "验证通过"`,
      explanation: `根据描述"${data.naturalLanguage}"生成的验证代码`,
    };
  },

  /**
   * 测试验证代码
   * @param data - 代码测试请求参数
   */
  async testCode(data: CodeTestRequest): Promise<CodeTestResponse> {
    // TODO: 替换为真实 API
    // return request.post<CodeTestResponse>('/quality-rules/test', data);
    await mockDelay(800);
    // 简单模拟：如果包含 age=16 则返回失败
    if (JSON.stringify(data.testData).includes('"age":16')) {
      return mockCodeTestFailure;
    }
    return mockCodeTestSuccess;
  },

  /**
   * 保存规则
   * @param rule - 规则数据
   */
  async saveRule(rule: Partial<QualityRule>): Promise<{ id: string }> {
    // TODO: 替换为真实 API
    // return request.post<{ id: string }>('/quality-rules', rule);
    await mockDelay(600);
    return { id: rule.id || `RULE-${Date.now()}` };
  },

  /**
   * 更新规则
   * @param id - 规则 ID
   * @param rule - 规则数据
   */
  async updateRule(_id: string, _rule: Partial<QualityRule>): Promise<void> {
    // TODO: 替换为真实 API
    // return request.put(`/quality-rules/${id}`, rule);
    await mockDelay(400);
  },
};

export default qualityRuleApi;
