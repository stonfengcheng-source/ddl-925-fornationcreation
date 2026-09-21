/**
 * MyTasks 页面
 * 我的任务管理 — 对接真实 /tasks API
 * 路径: /my-tasks
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import request from '@/services/request';
import {
  Layout,
  Row,
  Col,
  Card,
  Button,
  Tag,
  Progress,
  Spin,
  Space,
  Empty,
  Statistic,
  Table,
} from 'antd';
import {
  PlusOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  TeamOutlined,
  PlayCircleOutlined,
  DollarOutlined,
} from '@ant-design/icons';

import styles from './index.module.less';

const { Content } = Layout;

interface TaskItem {
  id: string;
  task_name: string;
  task_category: string;
  task_description: string;
  status: string;
  reward_pool: number;
  reward_currency: string;
  max_rounds: number;
  current_round: number;
  current_accuracy: number | null;
  participant_count: number;
  created_at: string;
}

const statusMap: Record<string, { color: string; text: string }> = {
  pending: { color: 'default', text: '待开始' },
  training: { color: 'processing', text: '训练中' },
  completed: { color: 'success', text: '已完成' },
  settled: { color: 'success', text: '已结算' },
  failed: { color: 'error', text: '失败' },
};

const MyTasks: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState<TaskItem[]>([]);

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const res: any = await request.get('/tasks');
      const list = res?.data || res || [];
      setTasks(Array.isArray(list) ? list : []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const stats = {
    total: tasks.length,
    training: tasks.filter((t) => t.status === 'training').length,
    completed: tasks.filter((t) => ['completed', 'settled'].includes(t.status)).length,
    totalReward: tasks.reduce((s, t) => s + (t.reward_pool || 0), 0),
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'task_name',
      key: 'task_name',
      ellipsis: true,
      render: (name: string, record: TaskItem) => (
        <a onClick={() => navigate(`/app/tasks/${record.id}`)}>{name}</a>
      ),
    },
    {
      title: '类别',
      dataIndex: 'task_category',
      key: 'task_category',
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => {
        const cfg = statusMap[s] || statusMap.pending;
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '训练进度',
      key: 'progress',
      width: 180,
      render: (_: any, record: TaskItem) => {
        const pct = record.max_rounds > 0 ? Math.round((record.current_round / record.max_rounds) * 100) : 0;
        return (
          <div>
            <Progress percent={pct} size="small" />
            <span style={{ fontSize: 12, color: '#999' }}>
              {record.current_round}/{record.max_rounds} 轮
            </span>
          </div>
        );
      },
    },
    {
      title: '参与节点',
      dataIndex: 'participant_count',
      key: 'participant_count',
      width: 90,
      render: (v: number) => v || 0,
    },
    {
      title: '奖励池',
      key: 'reward',
      width: 120,
      render: (_: any, record: TaskItem) => (
        <span style={{ color: '#fa8c16', fontWeight: 600 }}>
          ¥{(record.reward_pool || 0).toLocaleString()}
        </span>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (t: string) => (t ? new Date(t).toLocaleDateString() : '-'),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: TaskItem) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/app/tasks/${record.id}`)}>
            详情
          </Button>
          {['training', 'completed', 'settled'].includes(record.status) && (
            <Button
              size="small"
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => navigate(`/app/federated/training/${record.id}`)}
            >
              训练
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Content className={styles.myTasks}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0 }}>我的任务</h1>
          <p style={{ margin: 0, color: '#999' }}>管理您发布的联邦学习任务</p>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/app/tasks/publish')}>
          发布任务
        </Button>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="全部任务" value={stats.total} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="训练中" value={stats.training} prefix={<ClockCircleOutlined />} valueStyle={{ color: '#1890ff' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="已完成" value={stats.completed} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="总奖励池" value={stats.totalReward} prefix={<DollarOutlined />} suffix="CNY" valueStyle={{ color: '#fa8c16' }} />
          </Card>
        </Col>
      </Row>

      <Card>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin size="large" tip="加载任务列表..." />
          </div>
        ) : tasks.length > 0 ? (
          <Table
            columns={columns}
            dataSource={tasks}
            rowKey="id"
            pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
          />
        ) : (
          <Empty description="暂无任务，点击右上角发布新任务">
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/app/tasks/publish')}>
              发布任务
            </Button>
          </Empty>
        )}
      </Card>
    </Content>
  );
};

export default MyTasks;
