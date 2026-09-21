/**
 * Admin Dashboard 管理仪表盘页面
 * 路径: /admin
 * 对接真实 /admin/stats API
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import request from '@/services/request';
import {
  Row,
  Col,
  Card,
  Statistic,
  Button,
  Spin,
  Progress,
} from 'antd';
import {
  UserOutlined,
  ProjectOutlined,
  ClusterOutlined,
  ArrowRightOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import styles from './Dashboard.module.less';

interface AdminStats {
  totalUsers: number;
  totalTasks: number;
  totalNodes: number;
  onlineNodes: number;
  pendingTasks: number;
  trainingTasks: number;
  completedTasks: number;
  buyers: number;
  providers: number;
  totalDatasets: number;
  totalModels: number;
}

const AdminDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<AdminStats | null>(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const res: any = await request.get('/admin/stats');
      setStats(res?.data || res);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" tip="加载管理数据..." /></div>;
  }

  if (!stats) {
    return <div style={{ textAlign: 'center', padding: 80 }}>无法加载管理数据</div>;
  }

  const taskTotal = stats.totalTasks || 1;

  return (
    <div className={styles.dashboard}>
      <div className={styles.pageHeader}>
        <h1>管理仪表盘</h1>
        <p>平台运营数据总览</p>
      </div>

      {/* Row 1: 4 core stat cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={12} lg={6}>
          <Card hoverable onClick={() => navigate('/app/admin/users')} size="small">
            <Statistic title="用户总数" value={stats.totalUsers} prefix={<UserOutlined />} valueStyle={{ color: '#722ed1' }} />
            <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>
              需求方 {stats.buyers} · 提供方 {stats.providers}
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={12} lg={6}>
          <Card hoverable onClick={() => navigate('/app/admin/tasks')} size="small">
            <Statistic title="任务总数" value={stats.totalTasks} prefix={<ProjectOutlined />} valueStyle={{ color: '#1890ff' }} />
            <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>
              已完成 {stats.completedTasks}
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={12} lg={6}>
          <Card size="small">
            <Statistic title="节点 / 在线" value={stats.onlineNodes} suffix={`/ ${stats.totalNodes}`} prefix={<ClusterOutlined />} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
        <Col xs={12} sm={12} lg={6}>
          <Card size="small">
            <Statistic title="数据集 / 模型" value={stats.totalDatasets} suffix={`/ ${stats.totalModels}`} prefix={<DatabaseOutlined />} valueStyle={{ color: '#13c2c2' }} />
          </Card>
        </Col>
      </Row>

      {/* Row 2: Task pipeline + quick actions */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card title="任务状态分布" size="small">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '8px 0' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <ClockCircleOutlined style={{ color: '#faad14', fontSize: 16 }} />
                <span style={{ width: 72, fontSize: 13, color: '#666' }}>待开始</span>
                <Progress percent={Math.round((stats.pendingTasks / taskTotal) * 100)} strokeColor="#faad14" style={{ flex: 1, margin: 0 }} format={() => stats.pendingTasks} />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <PlayCircleOutlined style={{ color: '#1890ff', fontSize: 16 }} />
                <span style={{ width: 72, fontSize: 13, color: '#666' }}>训练中</span>
                <Progress percent={Math.round((stats.trainingTasks / taskTotal) * 100)} strokeColor="#1890ff" style={{ flex: 1, margin: 0 }} format={() => stats.trainingTasks} />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
                <span style={{ width: 72, fontSize: 13, color: '#666' }}>已完成</span>
                <Progress percent={Math.round((stats.completedTasks / taskTotal) * 100)} strokeColor="#52c41a" style={{ flex: 1, margin: 0 }} format={() => stats.completedTasks} />
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="快捷操作" size="small">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <Button type="primary" block icon={<ProjectOutlined />} onClick={() => navigate('/app/admin/tasks')}>
                任务管理 <ArrowRightOutlined />
              </Button>
              <Button block icon={<UserOutlined />} onClick={() => navigate('/app/admin/users')}>
                用户管理 <ArrowRightOutlined />
              </Button>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AdminDashboard;
