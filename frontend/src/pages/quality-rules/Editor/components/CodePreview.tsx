import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Copy, RefreshCw, AlertTriangle, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react';

interface CodePreviewProps {
  code: string;
  explanation?: string;
  warnings?: string[];
  loading?: boolean;
  onCopy?: () => void;
  onRegenerate?: () => void;
}

export const CodePreview: React.FC<CodePreviewProps> = ({
  code,
  explanation,
  warnings,
  loading,
  onCopy,
  onRegenerate,
}) => {
  const [showExplanation, setShowExplanation] = React.useState(true);
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    if (code) {
      navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      onCopy?.();
    }
  };

  // 简单的 Python 语法高亮
  const highlightPythonCode = (code: string): React.ReactNode => {
    if (!code) return null;

    const lines = code.split('\n');
    return lines.map((line, index) => {
      // 注释
      if (line.trim().startsWith('#')) {
        return (
          <div key={index} className="text-[#6a9955]">
            {line}
          </div>
        );
      }
      // 字符串（三引号）
      if (line.includes('"""') || line.includes("'''")) {
        return (
          <div key={index} className="text-[#ce9178]">
            {line}
          </div>
        );
      }
      // 关键字
      let highlighted = line
        .replace(/\b(def|return|if|else|elif|for|while|in|is|not|and|or|True|False|None|class|import|from|as|try|except|finally|with|yield|lambda|pass|break|continue)\b/g, '##$1##')
        .replace(/\b(\d+(?:\.\d+)?)\b/g, '%%$1%%')
        .replace(/(['"])(.*?)\1/g, '@@$1$2$1@@');

      const parts = highlighted.split(/(##.*?##|%%.*?%%|@@.*?@@)/g);

      return (
        <div key={index}>
          {parts.map((part, i) => {
            if (part.startsWith('##') && part.endsWith('##')) {
              return <span key={i} className="text-[#569cd6]">{part.slice(2, -2)}</span>;
            }
            if (part.startsWith('%%') && part.endsWith('%%')) {
              return <span key={i} className="text-[#b5cea8]">{part.slice(2, -2)}</span>;
            }
            if (part.startsWith('@@') && part.endsWith('@@')) {
              return <span key={i} className="text-[#ce9178]">{part.slice(2, -2)}</span>;
            }
            return <span key={i}>{part}</span>;
          })}
        </div>
      );
    });
  };

  return (
    <Card variant="neumorphic" className="h-full flex flex-col">
      <CardHeader className="flex flex-row justify-between items-center pb-2">
        <CardTitle className="text-lg">生成的验证代码</CardTitle>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleCopy}
            disabled={!code || loading}
          >
            {copied ? (
              <>
                <CheckCircle className="w-4 h-4 mr-1" />
                已复制
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 mr-1" />
                复制
              </>
            )}
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={onRegenerate}
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
            重新生成
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col space-y-4">
        {/* 警告信息 */}
        {warnings && warnings.length > 0 && (
          <div className="bg-[var(--accent-red)]/10 border border-[var(--accent-red)]/30 rounded-md p-3">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 text-[var(--accent-red)] flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-[var(--accent-red)]">警告</p>
                <ul className="mt-1 space-y-1">
                  {warnings.map((warning, index) => (
                    <li key={index} className="text-sm text-[var(--accent-red)]/80">
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* 代码说明 */}
        {explanation && (
          <div className="border border-border rounded-md overflow-hidden">
            <button
              className="w-full flex items-center justify-between p-3 bg-background-secondary hover:bg-background-tertiary transition-colors"
              onClick={() => setShowExplanation(!showExplanation)}
            >
              <span className="text-sm font-medium">代码说明</span>
              {showExplanation ? (
                <ChevronUp className="w-4 h-4 text-text-secondary" />
              ) : (
                <ChevronDown className="w-4 h-4 text-text-secondary" />
              )}
            </button>
            {showExplanation && (
              <div className="p-3 text-sm text-text-secondary bg-white">
                {explanation}
              </div>
            )}
          </div>
        )}

        {/* 代码展示 */}
        <div className="flex-1 neumorphic-inset bg-[#f7f6f3] rounded-md p-4 overflow-auto min-h-[300px]">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-full text-text-secondary">
              <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mb-3" />
              <p>AI 正在生成代码...</p>
            </div>
          ) : code ? (
            <pre className="font-mono text-sm text-text leading-relaxed whitespace-pre">
              {highlightPythonCode(code)}
            </pre>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-text-secondary">
              <p>在左侧输入规则描述并点击"生成验证代码"</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default CodePreview;
