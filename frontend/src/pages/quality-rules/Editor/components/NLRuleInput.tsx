import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { RuleType, FieldDefinition, RuleFormData } from '@/types/qualityRule';
import { Plus, Trash2, Sparkles } from 'lucide-react';

interface NLRuleInputProps {
  value: RuleFormData;
  onChange: (value: RuleFormData) => void;
  onGenerate: () => void;
  loading?: boolean;
}

// 常用模板
const templates = [
  { label: '年龄范围', text: '参与者年龄在{min}到{max}岁之间' },
  { label: '血压范围', text: '收缩压{systolic_min}-{systolic_max}，舒张压{diastolic_min}-{diastolic_max}' },
  { label: '数值范围', text: '数值字段{field}必须大于{min}且小于{max}' },
  { label: '字符串长度', text: '字符串字段{field}不能为空且长度在{min}-{max}之间' },
];

const ruleTypeOptions: { value: RuleType; label: string }[] = [
  { value: 'format', label: '格式验证' },
  { value: 'range', label: '范围验证' },
  { value: 'logic', label: '逻辑验证' },
  { value: 'custom', label: '自定义' },
];

const fieldTypeOptions: { value: FieldDefinition['type']; label: string }[] = [
  { value: 'string', label: '字符串' },
  { value: 'number', label: '数字' },
  { value: 'boolean', label: '布尔值' },
  { value: 'date', label: '日期' },
];

export const NLRuleInput: React.FC<NLRuleInputProps> = ({
  value,
  onChange,
  onGenerate,
  loading,
}) => {
  const [newFieldName, setNewFieldName] = useState('');
  const [newFieldType, setNewFieldType] = useState<FieldDefinition['type']>('string');
  const [newFieldDesc, setNewFieldDesc] = useState('');

  const handleAddField = () => {
    if (!newFieldName.trim()) return;
    const newField: FieldDefinition = {
      name: newFieldName.trim(),
      type: newFieldType,
      description: newFieldDesc.trim() || undefined,
    };
    onChange({
      ...value,
      fieldDefinitions: [...value.fieldDefinitions, newField],
    });
    setNewFieldName('');
    setNewFieldType('string');
    setNewFieldDesc('');
  };

  const handleRemoveField = (index: number) => {
    onChange({
      ...value,
      fieldDefinitions: value.fieldDefinitions.filter((_, i) => i !== index),
    });
  };

  const handleApplyTemplate = (templateText: string) => {
    onChange({
      ...value,
      description: templateText,
    });
  };

  return (
    <Card variant="neumorphic" className="h-full">
      <CardHeader>
        <CardTitle className="text-lg">规则定义</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 规则名称 */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-text-secondary">
            规则名称 <span className="text-accent-red">*</span>
          </label>
          <Input
            placeholder="请输入规则名称"
            value={value.name}
            onChange={(e) => onChange({ ...value, name: e.target.value })}
            maxLength={100}
          />
        </div>

        {/* 规则类型 */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-text-secondary">规则类型</label>
          <select
            className="w-full h-10 px-3 py-2 bg-white text-text text-sm border border-border-medium rounded-md focus:outline-none focus:ring-2 focus:ring-accent-blue neumorphic-inset"
            value={value.ruleType}
            onChange={(e) => onChange({ ...value, ruleType: e.target.value as RuleType })}
          >
            {ruleTypeOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* 常用模板 */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-text-secondary">常用模板</label>
          <div className="flex flex-wrap gap-2">
            {templates.map((tpl) => (
              <Button
                key={tpl.label}
                variant="secondary"
                size="sm"
                onClick={() => handleApplyTemplate(tpl.text)}
              >
                {tpl.label}
              </Button>
            ))}
          </div>
        </div>

        {/* 自然语言描述 */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-text-secondary">
            规则描述 <span className="text-accent-red">*</span>
          </label>
          <textarea
            className="neumorphic-inset w-full h-32 p-3 rounded-md bg-white text-text text-sm border border-border-medium focus:outline-none focus:ring-2 focus:ring-accent-blue resize-none"
            placeholder="用自然语言描述您的验证规则，例如：参与者年龄必须在18到65岁之间"
            value={value.description}
            onChange={(e) => onChange({ ...value, description: e.target.value })}
          />
        </div>

        {/* 字段定义 */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-text-secondary">字段定义</label>

          {/* 字段列表 */}
          {value.fieldDefinitions.length > 0 && (
            <div className="space-y-2 mb-3">
              {value.fieldDefinitions.map((field, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-2 bg-background-secondary rounded-md"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{field.name}</span>
                    <span className="text-xs text-text-secondary px-2 py-0.5 bg-white rounded">
                      {fieldTypeOptions.find((o) => o.value === field.type)?.label}
                    </span>
                    {field.description && (
                      <span className="text-xs text-text-secondary">{field.description}</span>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveField(index)}
                    className="text-accent-red hover:text-accent-red"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {/* 添加字段 */}
          <div className="flex gap-2">
            <Input
              placeholder="字段名"
              value={newFieldName}
              onChange={(e) => setNewFieldName(e.target.value)}
              className="flex-1"
            />
            <select
              className="h-10 px-3 py-2 bg-white text-text text-sm border border-border-medium rounded-md focus:outline-none focus:ring-2 focus:ring-accent-blue neumorphic-inset"
              value={newFieldType}
              onChange={(e) => setNewFieldType(e.target.value as FieldDefinition['type'])}
            >
              {fieldTypeOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <Button variant="secondary" size="sm" onClick={handleAddField}>
              <Plus className="w-4 h-4" />
            </Button>
          </div>
          <Input
            placeholder="字段描述（可选）"
            value={newFieldDesc}
            onChange={(e) => setNewFieldDesc(e.target.value)}
            className="mt-2"
          />
        </div>

        {/* 生成代码按钮 */}
        <Button
          variant="primary"
          effect="3d"
          onClick={onGenerate}
          disabled={loading || !value.name || !value.description}
          className="w-full mt-4"
        >
          {loading ? (
            <>
              <Sparkles className="w-4 h-4 mr-2 animate-spin" />
              生成中...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 mr-2" />
              生成验证代码
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
};

export default NLRuleInput;
