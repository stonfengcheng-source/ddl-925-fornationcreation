import React, { useState, useEffect } from 'react';
import request from '@/services/request';
import {
  Card,
  Avatar,
  Form,
  Input,
  Button,
  message,
  Row,
  Col,
  Select,
  Divider,
  Spin,
  Tag,
  Descriptions,
} from 'antd';
import {
  UserOutlined,
  MailOutlined,
  PhoneOutlined,
  EditOutlined,
  EnvironmentOutlined,
  CheckCircleOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import './index.less';

const { TextArea } = Input;
const { Option } = Select;

interface ProfileData {
  id: string;
  username: string;
  nickname: string;
  avatar: string;
  email: string;
  phone: string;
  bio: string;
  gender: string | null;
  location: string;
  userType: string;
  verified: boolean;
  balance: string;
  createdAt: string;
  lastLoginAt: string;
}

const Profile: React.FC = () => {
  const [form] = Form.useForm();
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const res: any = await request.get('/profile');
      const data = res?.data || res;
      setProfile(data);
      form.setFieldsValue(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProfile = async (values: any) => {
    setSaving(true);
    try {
      await request.put('/profile', {
        nickname: values.nickname,
        phone: values.phone,
        bio: values.bio,
        gender: values.gender,
        location: values.location,
      });
      message.success('个人资料更新成功');
      setIsEditing(false);
      fetchProfile();
    } catch {
      message.error('更新失败');
    } finally {
      setSaving(false);
    }
  };

  const roleMap: Record<string, { color: string; text: string }> = {
    buyer: { color: 'blue', text: '任务发布方' },
    provider: { color: 'green', text: '数据提供方' },
    admin: { color: 'red', text: '管理员' },
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" tip="加载个人资料..." />
      </div>
    );
  }

  if (!profile) return <div style={{ textAlign: 'center', padding: 80 }}>无法加载个人资料</div>;

  const roleCfg = roleMap[profile.userType] || roleMap.buyer;

  return (
    <div className="profile-page">
      <Card className="profile-card">
        <div className="profile-header">
          <div className="avatar-section">
            <Avatar size={100} icon={<UserOutlined />} src={profile.avatar || undefined} />
          </div>

          <div className="profile-info">
            <div className="username">
              {profile.nickname || profile.username}
              <Tag color={roleCfg.color} style={{ marginLeft: 12 }}>{roleCfg.text}</Tag>
              {profile.verified && (
                <Tag color="success" icon={<CheckCircleOutlined />}>已认证</Tag>
              )}
            </div>
            <div className="user-meta">
              <span className="meta-item"><MailOutlined /> {profile.email || '未设置'}</span>
              <span className="meta-item"><PhoneOutlined /> {profile.phone || '未设置'}</span>
              <span className="meta-item">
                <CalendarOutlined /> 注册于 {profile.createdAt ? new Date(profile.createdAt).toLocaleDateString() : '-'}
              </span>
            </div>
            {profile.bio && (
              <div style={{ marginTop: 8, color: 'rgba(0,0,0,0.65)' }}>{profile.bio}</div>
            )}
          </div>
        </div>

        <Divider />

        <Descriptions title="账户信息" bordered column={{ xs: 1, sm: 2 }} size="small" style={{ marginBottom: 24 }}>
          <Descriptions.Item label="用户ID">{profile.id}</Descriptions.Item>
          <Descriptions.Item label="用户名">{profile.username}</Descriptions.Item>
          <Descriptions.Item label="角色"><Tag color={roleCfg.color}>{roleCfg.text}</Tag></Descriptions.Item>
          <Descriptions.Item label="余额">¥{profile.balance}</Descriptions.Item>
          <Descriptions.Item label="实名认证">
            {profile.verified ? <Tag color="success">已认证</Tag> : <Tag color="warning">未认证</Tag>}
          </Descriptions.Item>
          <Descriptions.Item label="最后登录">
            {profile.lastLoginAt ? new Date(profile.lastLoginAt).toLocaleString() : '-'}
          </Descriptions.Item>
        </Descriptions>

        <div className="form-section">
          <div className="section-title">
            <EditOutlined /> 编辑资料
            {!isEditing && (
              <Button type="link" onClick={() => setIsEditing(true)}>编辑</Button>
            )}
          </div>

          <Form form={form} layout="vertical" onFinish={handleSaveProfile} disabled={!isEditing}>
            <Row gutter={24}>
              <Col xs={24} sm={12}>
                <Form.Item label="昵称" name="nickname">
                  <Input placeholder="请输入昵称" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item label="手机号" name="phone">
                  <Input prefix={<PhoneOutlined />} placeholder="请输入手机号" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item label="性别" name="gender">
                  <Select placeholder="请选择性别" allowClear>
                    <Option value="male">男</Option>
                    <Option value="female">女</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item label="所在地" name="location">
                  <Input prefix={<EnvironmentOutlined />} placeholder="请输入所在地" />
                </Form.Item>
              </Col>
              <Col span={24}>
                <Form.Item label="个人简介" name="bio">
                  <TextArea rows={3} placeholder="请输入个人简介" maxLength={200} showCount />
                </Form.Item>
              </Col>
            </Row>

            {isEditing && (
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={saving} style={{ marginRight: 8 }}>
                  保存
                </Button>
                <Button onClick={() => { setIsEditing(false); form.setFieldsValue(profile); }}>
                  取消
                </Button>
              </Form.Item>
            )}
          </Form>
        </div>
      </Card>
    </div>
  );
};

export default Profile;
