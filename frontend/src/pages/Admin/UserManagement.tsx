/**
 * User Management 用户管理页面
 * 路径: /admin/users — 对接 /admin/users API
 */

import React, { useState, useEffect } from 'react';
import request from '@/services/request';
import {
  Card,
  Table,
  Button,
  Input,
  Select,
  Tag,
  Space,
  Avatar,
  Row,
  Col,
  Statistic,
  Spin,
  Popconfirm,
  message,
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  UserOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import styles from './UserManagement.module.less';

const { Option } = Select;

interface UserItem {
  id: string;
  username: string;
  email: string;
  userType: string;
  status: string;
  balance: string;
  verified: boolean;
  createdAt: string;
  lastLoginAt: string;
}

const roleMap: Record<string, { color: string; text: string }> = {
  admin: { color: 'red', text: '管理员' },
  buyer: { color: 'blue', text: '任务发布方' },
  provider: { color: 'green', text: '数据提供方' },
};

const statusMap: Record<string, { color: string; text: string }> = {
  active: { color: 'success', text: '正常' },
  inactive: { color: 'default', text: '未激活' },
  suspended: { color: 'error', text: '已禁用' },
};

const UserManagement: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState<UserItem[]>([]);
  const [searchText, setSearchText] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (searchText) params.search = searchText;
      if (roleFilter !== 'all') params.user_type = roleFilter;
      const res: any = await request.get('/admin/users', { params });
      setUsers(res?.data || res || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, [roleFilter]);

  const handleDelete = async (userId: string) => {
    try {
      await request.delete(`/admin/users/${userId}`);
      message.success('用户已删除');
      loadUsers();
    } catch {
      message.error('删除失败');
    }
  };

  const filteredUsers = searchText
    ? users.filter(
        (u) =>
          u.username.toLowerCase().includes(searchText.toLowerCase()) ||
          u.email.toLowerCase().includes(searchText.toLowerCase())
      )
    : users;

  const stats = {
    total: users.length,
    active: users.filter((u) => u.status === 'active').length,
    buyers: users.filter((u) => u.userType === 'buyer').length,
    providers: users.filter((u) => u.userType === 'provider').length,
  };

  const columns = [
    {
      title: '用户信息',
      key: 'userInfo',
      render: (_: any, record: UserItem) => (
        <Space>
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
          <div>
            <div style={{ fontWeight: 500 }}>{record.username}</div>
            <div style={{ fontSize: 12, color: '#999' }}>{record.email}</div>
          </div>
        </Space>
      ),
    },
    {
      title: '角色',
      dataIndex: 'userType',
      key: 'userType',
      width: 120,
      render: (t: string) => {
        const cfg = roleMap[t] || { color: 'default', text: t };
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => {
        const cfg = statusMap[s] || statusMap.active;
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '余额',
      dataIndex: 'balance',
      key: 'balance',
      width: 100,
      render: (b: string) => `¥${b}`,
    },
    {
      title: '认证',
      dataIndex: 'verified',
      key: 'verified',
      width: 80,
      render: (v: boolean) => v ? <Tag color="success">已认证</Tag> : <Tag>未认证</Tag>,
    },
    {
      title: '注册时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 120,
      render: (t: string) => t ? new Date(t).toLocaleDateString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: UserItem) => (
        record.userType !== 'admin' ? (
          <Popconfirm
            title="确认删除"
            description={`确认删除用户「${record.username}」？将同时删除其所有数据。`}
            onConfirm={() => handleDelete(record.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        ) : <Tag color="red">管理员</Tag>
      ),
    },
  ];

  return (
    <div className={styles.userManagement}>
      <div className={styles.pageHeader}>
        <h1>用户管理</h1>
        <p>管理平台所有用户账号</p>
      </div>

      <Row gutter={[24, 24]} className={styles.statsRow}>
        <Col xs={12} sm={6}>
          <Card><Statistic title="总用户数" value={stats.total} prefix={<TeamOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="活跃用户" value={stats.active} valueStyle={{ color: '#52c41a' }} prefix={<CheckCircleOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="任务发布方" value={stats.buyers} prefix={<UserOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="数据提供方" value={stats.providers} prefix={<UserOutlined />} /></Card>
        </Col>
      </Row>

      <Card className={styles.filterCard}>
        <Space wrap>
          <Input
            placeholder="搜索用户名/邮箱"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            allowClear
            style={{ width: 220, minWidth: 140, maxWidth: '100%' }}
          />
          <Select value={roleFilter} onChange={setRoleFilter} style={{ width: 140, minWidth: 100 }}>
            <Option value="all">全部角色</Option>
            <Option value="buyer">任务发布方</Option>
            <Option value="provider">数据提供方</Option>
            <Option value="admin">管理员</Option>
          </Select>
          <Button icon={<ReloadOutlined />} onClick={loadUsers}>刷新</Button>
        </Space>
      </Card>

      <Card className={styles.tableCard}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
        ) : (
          <Table
            columns={columns}
            dataSource={filteredUsers}
            rowKey="id"
            scroll={{ x: 800 }}
            pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
          />
        )}
      </Card>
    </div>
  );
};

export default UserManagement;
