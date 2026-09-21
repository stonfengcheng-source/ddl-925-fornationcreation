import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useUserStore } from '@/store/useUserStore';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

/**
 * 登录页面
 * 使用项目UI组件，Notion风格设计
 */
const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useUserStore();
  const [loading, setLoading] = useState(false);

  const [formData, setFormData] = useState({
    username: '',
    password: '',
    remember: false,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  /**
   * 验证表单
   */
  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.username.trim()) {
      newErrors.username = '请输入用户名或邮箱';
    }
    if (!formData.password) {
      newErrors.password = '请输入密码';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  /**
   * 处理输入变化
   */
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
    // 清除对应字段的错误
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  /**
   * 处理登录提交（通过真实API登录）
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    try {
      const request = (await import('@/services/request')).default;
      const res: any = await request.post('/auth/login', {
        username: formData.username,
        password: formData.password,
        source: 'web',
      });
      const userData = res.user || res.data?.user;
      const token = res.token || res.data?.token;
      login({
        userId: userData.id,
        username: userData.username,
        email: userData.email || '',
        role: userData.user_type as any,
      }, token);
      message.success('登录成功');
      navigate('/app/dashboard');
    } catch (error: any) {
      console.error('登录失败:', error);
      const detail = error?.response?.data?.detail || error?.response?.data?.error?.message || '登录失败，请检查用户名和密码';
      message.error(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="gradient-flow min-h-screen flex items-center justify-center p-6">
      <Card variant="neumorphic" hoverEffect className="w-full max-w-md scale-in">
        <CardHeader className="text-center">
          <CardTitle className="gradient-text text-3xl">Data Task Platform</CardTitle>
          <CardDescription>联邦学习数据任务托管平台</CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4" autoComplete="off">
            {/* 用户名/邮箱 */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-primary">
                用户名/邮箱
              </label>
              <div className="relative">
                <UserOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                <Input
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  placeholder="请输入用户名或邮箱"
                  className="pl-10"
                  autoComplete="off"
                  error={!!errors.username}
                />
              </div>
              {errors.username && (
                <p className="text-sm text-accent-red">{errors.username}</p>
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
                  placeholder="请输入密码"
                  className="pl-10"
                  autoComplete="new-password"
                  error={!!errors.password}
                />
              </div>
              {errors.password && (
                <p className="text-sm text-accent-red">{errors.password}</p>
              )}
            </div>

            {/* 记住我和忘记密码 */}
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  name="remember"
                  checked={formData.remember}
                  onChange={handleChange}
                  className="w-4 h-4 rounded border-border-medium text-accent-blue focus:ring-accent-blue"
                />
                <span className="text-sm text-text-secondary">记住我</span>
              </label>
              <Link
                to="/forgot-password"
                className="text-sm text-accent-blue hover:underline"
              >
                忘记密码？
              </Link>
            </div>

            {/* 登录按钮 */}
            <Button
              type="submit"
              variant="primary"
              size="lg"
              effect="3d"
              className="w-full"
              disabled={loading}
            >
              {loading ? '登录中...' : '登录'}
            </Button>
          </form>

        </CardContent>

        <CardFooter className="justify-center">
          <span className="text-text-secondary text-sm">还没有账号？</span>
          <Link
            to="/register"
            className="ml-1 text-sm font-medium text-accent-blue hover:underline"
          >
            立即注册
          </Link>
        </CardFooter>
      </Card>
    </div>
  );
};

export default Login;
