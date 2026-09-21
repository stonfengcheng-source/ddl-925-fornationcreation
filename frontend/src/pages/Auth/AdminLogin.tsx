import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { message } from 'antd';
import { UserOutlined, LockOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { useUserStore } from '@/store/useUserStore';
import { DEFAULT_DEV_USERNAME, PASSWORDLESS_AUTH } from '@/utils/authMode';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

const AdminLogin: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useUserStore();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({ username: DEFAULT_DEV_USERNAME, password: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.username.trim()) newErrors.username = '请输入管理员账号';
    if (!PASSWORDLESS_AUTH && !formData.password) newErrors.password = '请输入密码';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    try {
      const request = (await import('@/services/request')).default;
      const res: any = await request.post('/auth/login', {
        username: formData.username,
        password: PASSWORDLESS_AUTH ? '' : formData.password,
        source: 'web',
      });
      const userData = res.user || res.data?.user;
      const token = res.token || res.data?.token;

      if (userData.user_type !== 'admin') {
        message.error('该账号不是管理员账号，请使用管理员账号登录');
        return;
      }

      login({
        userId: userData.id,
        username: userData.username,
        email: userData.email || '',
        role: userData.user_type as any,
      }, token);
      message.success('管理员登录成功');
      navigate('/app/admin');
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.response?.data?.error?.message || '登录失败，请检查账号和密码';
      message.error(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6" style={{
      background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 30%, #1e3a5f 60%, #0f172a 100%)',
    }}>
      <Card variant="neumorphic" hoverEffect className="w-full max-w-md scale-in">
        <CardHeader className="text-center">
          <div className="flex items-center justify-center mb-3">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
              <SafetyCertificateOutlined className="text-white text-2xl" />
            </div>
          </div>
          <CardTitle className="text-2xl text-gray-900">管理后台</CardTitle>
          <CardDescription>FedLearn Platform 管理员登录</CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4" autoComplete="off">
            <div className="space-y-2">
              <label className="text-sm font-medium text-text-primary">管理员账号</label>
              <div className="relative">
                <UserOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                <Input
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  placeholder="请输入管理员账号"
                  className="pl-10"
                  autoComplete="off"
                  error={!!errors.username}
                />
              </div>
              {errors.username && <p className="text-sm text-accent-red">{errors.username}</p>}
            </div>

            {!PASSWORDLESS_AUTH ? (
              <div className="space-y-2">
                <label className="text-sm font-medium text-text-primary">密码</label>
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
                {errors.password && <p className="text-sm text-accent-red">{errors.password}</p>}
              </div>
            ) : (
              <p className="text-sm text-text-secondary">
                当前为本地开发免密模式，默认使用 admin 账号。
              </p>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              effect="3d"
              className="w-full"
              disabled={loading}
            >
              {loading ? '登录中...' : '管理员登录'}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <Link to="/" className="text-sm text-accent-blue hover:underline">
              返回首页
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminLogin;
