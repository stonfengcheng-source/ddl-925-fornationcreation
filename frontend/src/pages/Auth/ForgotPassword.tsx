import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { message } from 'antd';
import { MailOutlined, SafetyOutlined, LockOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { authApi } from '@/services/api/auth';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

/**
 * 忘记密码页面
 * 三步流程：输入邮箱 -> 输入验证码和新密码 -> 重置成功
 * 使用项目UI组件，Notion风格设计
 */
const ForgotPassword: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [formData, setFormData] = useState({
    code: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  // 倒计时效果
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  /**
   * 处理输入变化
   */
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  /**
   * 渲染步骤指示器
   */
  const renderStepIndicator = () => {
    const steps = ['输入邮箱', '验证重置', '完成'];
    return (
      <div className="flex items-center justify-center mb-8">
        {steps.map((step, index) => (
          <React.Fragment key={index}>
            {/* 步骤圆点 */}
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                  index < currentStep
                    ? 'bg-green-500 text-white'
                    : index === currentStep
                    ? 'bg-accent-blue text-white'
                    : 'bg-bg-tertiary text-text-secondary'
                }`}
              >
                {index < currentStep ? (
                  <CheckCircleOutlined />
                ) : (
                  index + 1
                )}
              </div>
              <span
                className={`text-xs mt-1 ${
                  index <= currentStep ? 'text-text-primary' : 'text-text-secondary'
                }`}
              >
                {step}
              </span>
            </div>
            {/* 连接线 */}
            {index < steps.length - 1 && (
              <div
                className={`w-16 h-0.5 mx-2 transition-colors ${
                  index < currentStep ? 'bg-green-500' : 'bg-border-medium'
                }`}
              />
            )}
          </React.Fragment>
        ))}
      </div>
    );
  };

  /**
   * 第一步：发送验证码
   */
  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      setErrors({ email: '请输入邮箱' });
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setErrors({ email: '请输入有效的邮箱地址' });
      return;
    }

    setLoading(true);
    try {
      await authApi.sendResetCode(email);
      message.success('验证码已发送到您的邮箱');
      setCurrentStep(1);
      setCountdown(60);
    } catch (error) {
      console.error('发送验证码失败:', error);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 重新发送验证码
   */
  const handleResendCode = async () => {
    if (countdown > 0) return;
    setLoading(true);
    try {
      await authApi.sendResetCode(email);
      message.success('验证码已重新发送');
      setCountdown(60);
    } catch (error) {
      console.error('发送验证码失败:', error);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 第二步：重置密码
   */
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};

    if (!formData.code.trim()) {
      newErrors.code = '请输入验证码';
    }

    if (!formData.newPassword) {
      newErrors.newPassword = '请输入新密码';
    } else if (formData.newPassword.length < 8) {
      newErrors.newPassword = '密码至少8位';
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.newPassword)) {
      newErrors.newPassword = '密码必须包含大小写字母和数字';
    }

    if (formData.newPassword !== formData.confirmPassword) {
      newErrors.confirmPassword = '两次输入的密码不一致';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setLoading(true);
    try {
      await authApi.resetPassword({
        email,
        code: formData.code,
        newPassword: formData.newPassword,
      });

      message.success('密码重置成功');
      setCurrentStep(2);

      // 3秒后跳转到登录页面
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (error) {
      console.error('重置密码失败:', error);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 渲染步骤内容
   */
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <form onSubmit={handleSendCode} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-primary">
                邮箱
              </label>
              <div className="relative">
                <MailOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (errors.email) setErrors({});
                  }}
                  placeholder="请输入注册时使用的邮箱"
                  className="pl-10"
                  error={!!errors.email}
                />
              </div>
              {errors.email && (
                <p className="text-sm text-accent-red">{errors.email}</p>
              )}
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              effect="3d"
              className="w-full"
              disabled={loading}
            >
              {loading ? '发送中...' : '发送验证码'}
            </Button>

            <div className="text-center">
              <Link
                to="/login"
                className="text-sm text-accent-blue hover:underline"
              >
                返回登录
              </Link>
            </div>
          </form>
        );

      case 1:
        return (
          <form onSubmit={handleResetPassword} className="space-y-4">
            <p className="text-sm text-text-secondary text-center">
              验证码已发送至 <span className="text-text-primary font-medium">{email}</span>
            </p>

            {/* 验证码 */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-primary">
                验证码
              </label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <SafetyOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                  <Input
                    name="code"
                    value={formData.code}
                    onChange={handleChange}
                    placeholder="请输入6位验证码"
                    maxLength={6}
                    className="pl-10"
                    error={!!errors.code}
                  />
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleResendCode}
                  disabled={countdown > 0 || loading}
                >
                  {countdown > 0 ? `${countdown}s` : '重新发送'}
                </Button>
              </div>
              {errors.code && (
                <p className="text-sm text-accent-red">{errors.code}</p>
              )}
            </div>

            {/* 新密码 */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-primary">
                新密码
              </label>
              <div className="relative">
                <LockOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                <Input
                  name="newPassword"
                  type="password"
                  value={formData.newPassword}
                  onChange={handleChange}
                  placeholder="至少8位，包含大小写字母和数字"
                  className="pl-10"
                  error={!!errors.newPassword}
                />
              </div>
              {errors.newPassword && (
                <p className="text-sm text-accent-red">{errors.newPassword}</p>
              )}
            </div>

            {/* 确认新密码 */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-primary">
                确认新密码
              </label>
              <div className="relative">
                <LockOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                <Input
                  name="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="请再次输入新密码"
                  className="pl-10"
                  error={!!errors.confirmPassword}
                />
              </div>
              {errors.confirmPassword && (
                <p className="text-sm text-accent-red">{errors.confirmPassword}</p>
              )}
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              effect="3d"
              className="w-full"
              disabled={loading}
            >
              {loading ? '重置中...' : '重置密码'}
            </Button>

            <Button
              type="button"
              variant="ghost"
              className="w-full"
              onClick={() => setCurrentStep(0)}
            >
              返回上一步
            </Button>
          </form>
        );

      case 2:
        return (
          <div className="text-center py-6">
            <div className="w-16 h-16 rounded-full bg-green-500 flex items-center justify-center mx-auto mb-4">
              <CheckCircleOutlined className="text-white text-2xl" />
            </div>
            <h3 className="text-xl font-semibold text-text-primary mb-2">
              密码重置成功
            </h3>
            <p className="text-text-secondary mb-6">
              您的密码已成功重置，3秒后自动跳转到登录页面...
            </p>
            <Link to="/login">
              <Button variant="primary" effect="3d">
                立即登录
              </Button>
            </Link>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="gradient-flow min-h-screen flex items-center justify-center p-6">
      <Card variant="neumorphic" hoverEffect className="w-full max-w-md scale-in">
        <CardHeader className="text-center">
          <CardTitle className="gradient-text text-3xl">找回密码</CardTitle>
          <CardDescription>通过邮箱验证重置您的密码</CardDescription>
        </CardHeader>

        <CardContent>
          {renderStepIndicator()}
          {renderStepContent()}
        </CardContent>
      </Card>
    </div>
  );
};

export default ForgotPassword;
