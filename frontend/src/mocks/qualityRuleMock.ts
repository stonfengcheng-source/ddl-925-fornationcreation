import { QualityRule, CodeGenerationResponse, CodeTestResponse } from '../types/qualityRule';

// 示例规则 1：年龄范围验证
export const mockQualityRule1: QualityRule = {
  id: 'RULE-001',
  name: '参与者年龄验证',
  description: '参与者年龄必须在18到65岁之间',
  ruleType: 'range',
  fieldDefinitions: [
    { name: 'age', type: 'number', description: '参与者年龄' }
  ],
  generatedCode: `def validate(data):
    """
    验证参与者年龄是否在18-65岁之间
    """
    age = data.get('age')

    # 检查年龄是否存在
    if age is None:
        return False, "年龄字段缺失"

    # 检查年龄是否为数字
    if not isinstance(age, (int, float)):
        return False, "年龄必须是数字"

    # 检查年龄范围
    if 18 <= age <= 65:
        return True, "验证通过"
    else:
        return False, f"年龄{age}不在有效范围18-65岁之间"`,
  codeExplanation: '该验证函数检查数据中的 age 字段是否存在、是否为数字，以及是否在 18-65 岁的有效范围内。',
  testCases: [
    {
      id: 'TC-001',
      name: '有效年龄',
      input: { age: 25 },
      expectedResult: true,
      actualResult: true,
    },
    {
      id: 'TC-002',
      name: '年龄过小',
      input: { age: 16 },
      expectedResult: false,
      actualResult: false,
    },
    {
      id: 'TC-003',
      name: '年龄缺失',
      input: {},
      expectedResult: false,
    },
  ],
  status: 'active',
  createdAt: '2026-02-01T10:00:00Z',
  updatedAt: '2026-02-01T10:30:00Z',
};

// 示例规则 2：血压范围验证
export const mockQualityRule2: QualityRule = {
  id: 'RULE-002',
  name: '血压范围验证',
  description: '收缩压90-140，舒张压60-90',
  ruleType: 'range',
  fieldDefinitions: [
    { name: 'systolic', type: 'number', description: '收缩压' },
    { name: 'diastolic', type: 'number', description: '舒张压' },
  ],
  generatedCode: `def validate(data):
    """
    验证血压范围：收缩压90-140，舒张压60-90
    """
    systolic = data.get('systolic')
    diastolic = data.get('diastolic')

    if systolic is None or diastolic is None:
        return False, "血压数据缺失"

    if not (90 <= systolic <= 140):
        return False, f"收缩压{systolic}不在正常范围(90-140)"

    if not (60 <= diastolic <= 90):
        return False, f"舒张压{diastolic}不在正常范围(60-90)"

    return True, "血压正常"`,
  codeExplanation: '验证血压的收缩压和舒张压是否在正常范围内。',
  testCases: [
    { id: 'TC-004', name: '正常血压', input: { systolic: 120, diastolic: 80 }, expectedResult: true },
    { id: 'TC-005', name: '高血压', input: { systolic: 150, diastolic: 80 }, expectedResult: false },
  ],
  status: 'active',
  createdAt: '2026-02-02T09:00:00Z',
  updatedAt: '2026-02-02T09:15:00Z',
};

// 示例规则 3：邮箱格式验证（草稿状态）
export const mockQualityRule3: QualityRule = {
  id: 'RULE-003',
  name: '邮箱格式验证',
  description: '验证邮箱地址格式是否正确，支持常见邮箱域名',
  ruleType: 'format',
  fieldDefinitions: [
    { name: 'email', type: 'string', description: '邮箱地址' },
  ],
  generatedCode: `def validate(data):
    """
    验证邮箱格式是否正确
    """
    import re
    email = data.get('email')

    if not email:
        return False, "邮箱地址不能为空"

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True, "邮箱格式正确"
    else:
        return False, f"邮箱格式不正确: {email}"`,
  codeExplanation: '使用正则表达式验证邮箱格式是否符合标准格式。',
  testCases: [
    { id: 'TC-006', name: '有效邮箱', input: { email: 'test@example.com' }, expectedResult: true },
    { id: 'TC-007', name: '无效邮箱', input: { email: 'invalid-email' }, expectedResult: false },
    { id: 'TC-008', name: '空邮箱', input: { email: '' }, expectedResult: false },
  ],
  status: 'draft',
  createdAt: '2026-02-05T14:00:00Z',
  updatedAt: '2026-02-08T10:30:00Z',
};

// 示例规则 4：手机号格式验证（草稿状态）
export const mockQualityRule4: QualityRule = {
  id: 'RULE-004',
  name: '手机号格式验证',
  description: '验证中国大陆手机号格式（11位数字，以1开头）',
  ruleType: 'format',
  fieldDefinitions: [
    { name: 'phone', type: 'string', description: '手机号码' },
  ],
  generatedCode: `def validate(data):
    """
    验证中国大陆手机号格式
    """
    phone = data.get('phone')

    if not phone:
        return False, "手机号不能为空"

    if not isinstance(phone, str):
        phone = str(phone)

    if len(phone) == 11 and phone.startswith('1') and phone.isdigit():
        return True, "手机号格式正确"
    else:
        return False, f"手机号格式不正确: {phone}"`,
  codeExplanation: '验证手机号是否为11位数字且以1开头。',
  testCases: [
    { id: 'TC-009', name: '有效手机号', input: { phone: '13800138000' }, expectedResult: true },
    { id: 'TC-010', name: '无效手机号', input: { phone: '1234567890' }, expectedResult: false },
  ],
  status: 'draft',
  createdAt: '2026-02-06T11:00:00Z',
  updatedAt: '2026-02-08T11:00:00Z',
};

// 示例规则 5：逻辑验证 - 身份证与姓名匹配（禁用状态）
export const mockQualityRule5: QualityRule = {
  id: 'RULE-005',
  name: '身份证与姓名一致性验证',
  description: '验证身份证号码与提供的姓名是否匹配',
  ruleType: 'logic',
  fieldDefinitions: [
    { name: 'idCard', type: 'string', description: '身份证号码' },
    { name: 'name', type: 'string', description: '姓名' },
  ],
  generatedCode: `def validate(data):
    """
    验证身份证与姓名是否匹配（需要外部API支持）
    """
    id_card = data.get('idCard')
    name = data.get('name')

    if not id_card or not name:
        return False, "身份证和姓名不能为空"

    # 简单校验身份证格式
    if len(id_card) != 18:
        return False, "身份证号码长度不正确"

    # TODO: 调用实名认证API
    return True, "身份证格式正确（未调用实名认证）"`,
  codeExplanation: '校验身份证格式并预留实名认证接口调用。',
  testCases: [
    { id: 'TC-011', name: '格式正确', input: { idCard: '110101199001011234', name: '张三' }, expectedResult: true },
    { id: 'TC-012', name: '格式错误', input: { idCard: '123456', name: '张三' }, expectedResult: false },
  ],
  status: 'disabled',
  createdAt: '2026-02-01T08:00:00Z',
  updatedAt: '2026-02-03T16:00:00Z',
};

// 示例规则 6：自定义验证 - 产品价格范围
export const mockQualityRule6: QualityRule = {
  id: 'RULE-006',
  name: '产品价格范围验证',
  description: '验证产品价格是否在合理范围内（0-100000元）',
  ruleType: 'custom',
  fieldDefinitions: [
    { name: 'price', type: 'number', description: '产品价格' },
    { name: 'currency', type: 'string', description: '货币类型' },
  ],
  generatedCode: `def validate(data):
    """
    验证产品价格是否在合理范围内
    """
    price = data.get('price')
    currency = data.get('currency', 'CNY')

    if price is None:
        return False, "价格不能为空"

    if not isinstance(price, (int, float)):
        return False, "价格必须是数字"

    if price < 0:
        return False, "价格不能为负数"

    if price > 100000:
        return False, f"价格{price}超过最大限制(100000)"

    return True, f"价格合法: {price} {currency}"`,
  codeExplanation: '验证产品价格是否为数字且在0-100000范围内。',
  testCases: [
    { id: 'TC-013', name: '正常价格', input: { price: 999, currency: 'CNY' }, expectedResult: true },
    { id: 'TC-014', name: '过高价格', input: { price: 200000, currency: 'CNY' }, expectedResult: false },
    { id: 'TC-015', name: '负数价格', input: { price: -100, currency: 'CNY' }, expectedResult: false },
  ],
  status: 'active',
  createdAt: '2026-02-07T09:00:00Z',
  updatedAt: '2026-02-09T10:00:00Z',
};

// 所有规则列表
export const mockQualityRules: QualityRule[] = [
  mockQualityRule1,
  mockQualityRule2,
  mockQualityRule3,
  mockQualityRule4,
  mockQualityRule5,
  mockQualityRule6,
];

// 代码生成响应模拟
export const mockCodeGenerationResponse: CodeGenerationResponse = {
  success: true,
  code: `def validate(data):\n    pass`,
  explanation: '根据您的描述生成的验证代码',
  warnings: [],
};

// 代码测试响应模拟
export const mockCodeTestSuccess: CodeTestResponse = {
  success: true,
  result: true,
  executionTime: 12,
};

export const mockCodeTestFailure: CodeTestResponse = {
  success: true,
  result: false,
  error: '年龄16不在有效范围18-65岁之间',
  executionTime: 8,
};

// 默认导出
export const qualityRuleMock = {
  rules: mockQualityRules,
  rule1: mockQualityRule1,
  rule2: mockQualityRule2,
  generationResponse: mockCodeGenerationResponse,
  testSuccess: mockCodeTestSuccess,
  testFailure: mockCodeTestFailure,
};

export default qualityRuleMock;
