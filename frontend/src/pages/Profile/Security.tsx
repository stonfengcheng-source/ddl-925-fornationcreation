import React, { useState } from 'react';
import request from '@/services/request';
import { PASSWORDLESS_AUTH } from '@/utils/authMode';
import {
  Card,
  Form,
  Input,
  Button,
  message,
} from 'antd';
import {
  LockOutlined,
  SecurityScanOutlined,
} from '@ant-design/icons';
import './index.less';

const Security: React.FC = () => {
  const [passwordForm] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleChangePassword = async (values: any) => {
    setLoading(true);
    try {
      await request.put('/profile/password', {
        current_password: values.currentPassword,
        new_password: values.newPassword,
      });
      message.success('密码修改成功');
      passwordForm.resetFields();
    } catch {
      // error interceptor handles it
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="profile-page">
      <Card style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <SecurityScanOutlined style={{ fontSize: 48, color: '#52c41a' }} />
          <div>
            <h3 style={{ margin: 0, fontSize: 18 }}>账户安全</h3>
            <p style={{ margin: '8px 0 0 0', color: 'rgba(0,0,0,0.45)' }}>
              管理您的账户密码安全设置
            </p>
          </div>
        </div>
      </Card>

      {PASSWORDLESS_AUTH ? (
        <Card title="登录方式">
          <p style={{ margin: 0, color: 'rgba(0,0,0,0.65)' }}>
            当前为本地开发免密模式，无需设置或修改账户密码。
          </p>
        </Card>
      ) : (
        <Card
          title={
            <span>
              <LockOutlined style={{ marginRight: 8 }} />
              修改密码
            </span>
          }
        >
          <Form
            form={passwordForm}
            layout="vertical"
            onFinish={handleChangePassword}
            style={{ maxWidth: 400 }}
          >
          <Form.Item
            label="当前密码"
            name="currentPassword"
            rules={[{ required: true, message: '请输入当前密码' }]}
          >
            <Input.Password placeholder="请输入当前密码" />
          </Form.Item>
          <Form.Item
            label="新密码"
            name="newPassword"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码长度至少6位' },
            ]}
          >
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
          <Form.Item
            label="确认新密码"
            name="confirmPassword"
            dependencies={['newPassword']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="请确认新密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>
              确认修改
            </Button>
          </Form.Item>
          </Form>
        </Card>
      )}
    </div>
  );
};

export default Security;
