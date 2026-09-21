import React, { useState, useEffect } from 'react';
import request from '@/services/request';
import {
  Card,
  Badge,
  Button,
  Tag,
  Space,
  List,
  Spin,
  Row,
  Col,
  Statistic,
  message,
  Empty,
} from 'antd';
import {
  BellOutlined,
  CheckCircleOutlined,
  DeleteOutlined,
  ReloadOutlined,
  InboxOutlined,
} from '@ant-design/icons';
import './index.less';

interface NotifItem {
  id: string;
  type: string;
  title: string;
  content: string;
  isRead: boolean;
  priority: string;
  createdAt: string;
}

interface NotifStats {
  total: number;
  unread: number;
}

const Notifications: React.FC = () => {
  const [notifications, setNotifications] = useState<NotifItem[]>([]);
  const [stats, setStats] = useState<NotifStats>({ total: 0, unread: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [listRes, statsRes]: any[] = await Promise.all([
        request.get('/notifications'),
        request.get('/notifications/stats'),
      ]);
      setNotifications(listRes?.data || listRes || []);
      const s = statsRes?.data || statsRes || {};
      setStats({ total: s.total || 0, unread: s.unread || 0 });
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleMarkAsRead = async (id: string) => {
    try {
      await request.put(`/notifications/${id}/read`);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, isRead: true } : n))
      );
      setStats((prev) => ({ ...prev, unread: Math.max(0, prev.unread - 1) }));
    } catch {
      message.error('操作失败');
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await request.put('/notifications/read-all');
      setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
      setStats((prev) => ({ ...prev, unread: 0 }));
      message.success('全部标记已读');
    } catch {
      message.error('操作失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await request.delete(`/notifications/${id}`);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      setStats((prev) => ({ ...prev, total: Math.max(0, prev.total - 1) }));
      message.success('已删除');
    } catch {
      message.error('删除失败');
    }
  };

  return (
    <div className="notifications-page">
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={8}>
          <Card>
            <Statistic title="全部通知" value={stats.total} prefix={<BellOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card>
            <Statistic title="未读通知" value={stats.unread} valueStyle={{ color: '#ff4d4f' }} prefix={<InboxOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <Space>
              <Button icon={<CheckCircleOutlined />} onClick={handleMarkAllAsRead} disabled={stats.unread === 0}>
                全部已读
              </Button>
              <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
            </Space>
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <Space>
            <BellOutlined />
            <span>消息中心</span>
            {stats.unread > 0 && <Badge count={stats.unread} />}
          </Space>
        }
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
        ) : notifications.length === 0 ? (
          <Empty description="暂无通知消息" />
        ) : (
          <List
            dataSource={notifications}
            renderItem={(item) => (
              <List.Item
                style={{ background: item.isRead ? 'transparent' : '#f0f5ff', padding: '12px 16px', borderRadius: 6, marginBottom: 8 }}
                actions={[
                  !item.isRead && (
                    <Button key="read" type="link" size="small" onClick={() => handleMarkAsRead(item.id)}>
                      标记已读
                    </Button>
                  ),
                  <Button key="del" type="link" danger size="small" icon={<DeleteOutlined />} onClick={() => handleDelete(item.id)} />,
                ].filter(Boolean)}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      {!item.isRead && <Badge dot />}
                      <span>{item.title}</span>
                      {item.priority === 'high' && <Tag color="error">重要</Tag>}
                      <Tag>{item.type}</Tag>
                    </Space>
                  }
                  description={
                    <div>
                      <div>{item.content}</div>
                      <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                        {item.createdAt ? new Date(item.createdAt).toLocaleString() : ''}
                      </div>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
};

export default Notifications;
