import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { message } from 'antd';
import { UserOutlined, MailOutlined, LockOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { authApi } from '@/services/api/auth';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

/**
 * 注册页面
 * 使用项目UI组件，Notion风格设计
 */
const Register: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    userType: '',
    agreement: false,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  /**
   * 验证密码
   */
  const validatePassword = (password: string) => {
    if (!password) return '请输入密码';
    if (password.length < 8) return '密码至少8位';
    if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(password)) {
      return '密码必须包含大小写字母和数字';
    }
    return '';
  };

  /**
   * 验证表单
   */
  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.username.trim()) {
      newErrors.username = '请输入用户名';
    } else if (formData.username.length < 3) {
      newErrors.username = '用户名至少3个字符';
    } else if (formData.username.length > 20) {
      newErrors.username = '用户名最多20个字符';
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.username)) {
      newErrors.username = '用户名只能包含字母、数字和下划线';
    }

    if (!formData.email.trim()) {
      newErrors.email = '请输入邮箱';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = '请输入有效的邮箱地址';
    }

    const passwordError = validatePassword(formData.password);
    if (passwordError) {
      newErrors.password = passwordError;
    }

    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = '两次输入的密码不一致';
    }

    if (!formData.userType) {
      newErrors.userType = '请选择用户类型';
    }

    if (!formData.agreement) {
      newErrors.agreement = '请同意用户协议和隐私政策';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  /**
   * 处理输入变化
   */
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    const checked = (e.target as HTMLInputElement).checked;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  /**
   * 处理注册提交
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    try {
      await authApi.register({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        userType: formData.userType as 'buyer' | 'provider',
      });

      message.success('注册成功，请登录');
      navigate('/login');
    } catch (error) {
      console.error('注册失败:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="gradient-flow min-h-screen flex items-center justify-center p-6">
      <Card variant="neumorphic" hoverEffect className="w-full max-w-md scale-in">
        <CardHeader className="text-center">
          <CardTitle className="gradient-text text-3xl">创建账号</CardTitle>
          <CardDescription>加入 Data Task Platform，开启联邦学习之旅</CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 用户名 */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-primary">
                用户名
              </label>
              <div className="relative">
                <UserOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                <Input
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  placeholder="请输入用户名"
                  className="pl-10"
                  error={!!errors.username}
                />
              </div>
              {errors.username && (
                <p className="text-sm text-accent-red">{errors.username}</p>
              )}
            </div>

            {/* 邮箱 */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-primary">
                邮箱
              </label>
              <div className="relative">
                <MailOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                <Input
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="请输入邮箱"
                  className="pl-10"
                  error={!!errors.email}
                />
              </div>
              {errors.email && (
                <p className="text-sm text-accent-red">{errors.email}</p>
              )}
            </div>

            {/* 密码 */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-primary">
                密码
              </label>
              <div className="relative">
                <LockOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                <Input
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="至少8位，包含大小写字母和数字"
                  className="pl-10"
                  error={!!errors.password}
                />
              </div>
              {errors.password && (
                <p className="text-sm text-accent-red">{errors.password}</p>
              )}
            </div>

            {/* 确认密码 */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-primary">
                确认密码
              </label>
              <div className="relative">
                <CheckCircleOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                <Input
                  name="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="请再次输入密码"
                  className="pl-10"
                  error={!!errors.confirmPassword}
                />
              </div>
              {errors.confirmPassword && (
                <p className="text-sm text-accent-red">{errors.confirmPassword}</p>
              )}
            </div>

            {/* 用户类型 */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-primary">
                用户类型
              </label>
              <select
                name="userType"
                value={formData.userType}
                onChange={handleChange}
                className={`w-full h-10 px-3 py-2 bg-white text-text text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-accent-blue focus:border-transparent transition-all duration-150 neumorphic-inset ${
                  errors.userType ? 'border-accent-red focus:ring-accent-red' : 'border-border-medium'
                }`}
              >
                <option value="">请选择用户类型</option>
                <option value="buyer">任务发布者 - 我需要数据训练模型</option>
                <option value="provider">数据提供方 - 我有数据可以共享</option>
              </select>
              {errors.userType && (
                <p className="text-sm text-accent-red">{errors.userType}</p>
              )}
            </div>

            {/* 用户协议 */}
            <div className="space-y-2">
              <label className="flex items-start gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  name="agreement"
                  checked={formData.agreement}
                  onChange={handleChange}
                  className="w-4 h-4 mt-0.5 rounded border-border-medium text-accent-blue focus:ring-accent-blue"
                />
                <span className="text-sm text-text-secondary">
                  我已阅读并同意
                  <a
                    href="#"
                    onClick={(e) => { e.preventDefault(); message.info('用户协议开发中...'); }}
                    className="text-accent-blue hover:underline mx-1"
                  >
                    用户协议
                  </a>
                  和
                  <a
                    href="#"
                    onClick={(e) => { e.preventDefault(); message.info('隐私政策开发中...'); }}
                    className="text-accent-blue hover:underline mx-1"
                  >
                    隐私政策
                  </a>
                </span>
              </label>
              {errors.agreement && (
                <p className="text-sm text-accent-red">{errors.agreement}</p>
              )}
            </div>

            {/* 注册按钮 */}
            <Button
              type="submit"
              variant="primary"
              size="lg"
              effect="3d"
              className="w-full"
              disabled={loading}
            >
              {loading ? '注册中...' : '注册'}
            </Button>
          </form>
        </CardContent>

        <CardFooter className="justify-center">
          <span className="text-text-secondary text-sm">已有账号？</span>
          <Link
            to="/login"
            className="ml-1 text-sm font-medium text-accent-blue hover:underline"
          >
            立即登录
          </Link>
        </CardFooter>
      </Card>
    </div>
  );
};

export default Register;
