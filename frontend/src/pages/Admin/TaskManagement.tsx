/**
 * Task Management 任务管理页面
 * 路径: /admin/tasks — 对接 /admin/tasks API
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import request from '@/services/request';
import {
  Card,
  Table,
  Button,
  Input,
  Select,
  Tag,
  Space,
  Progress,
  Row,
  Col,
  Statistic,
  Spin,
  Popconfirm,
  Modal,
  Checkbox,
  message,
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  EyeOutlined,
  DeleteOutlined,
  SendOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ProjectOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import styles from './TaskManagement.module.less';

const { Option } = Select;

interface TaskItem {
  id: string;
  name: string;
  publisher: string;
  category: string;
  status: string;
  rewardPool: number;
  currentRound: number;
  maxRounds: number;
  createdAt: string;
}

const statusMap: Record<string, { color: string; text: string }> = {
  pending: { color: 'default', text: '待开始' },
  training: { color: 'processing', text: '训练中' },
  completed: { color: 'success', text: '已完成' },
  settled: { color: 'success', text: '已结算' },
  failed: { color: 'error', text: '失败' },
};

interface ProviderItem {
  id: string;
  username: string;
  email: string;
  hasNode: boolean;
  nodeName: string;
}

const TaskManagement: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [recommendModal, setRecommendModal] = useState(false);
  const [recommendTaskId, setRecommendTaskId] = useState('');
  const [providers, setProviders] = useState<ProviderItem[]>([]);
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [recommending, setRecommending] = useState(false);

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      const res: any = await request.get('/admin/tasks', { params });
      setTasks(res?.data || res || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, [statusFilter]);

  const handleDelete = async (taskId: string) => {
    try {
      await request.delete(`/admin/tasks/${taskId}`);
      message.success('任务已删除');
      loadTasks();
    } catch {
      message.error('删除失败');
    }
  };

  const openRecommendModal = async (taskId: string) => {
    setRecommendTaskId(taskId);
    setSelectedProviders([]);
    try {
      const res: any = await request.get('/admin/providers');
      setProviders(res?.data || res || []);
    } catch {
      setProviders([]);
    }
    setRecommendModal(true);
  };

  const handleRecommend = async () => {
    if (selectedProviders.length === 0) {
      message.warning('请选择至少一个数据提供方');
      return;
    }
    setRecommending(true);
    try {
      const res: any = await request.post('/admin/recommend-task', {
        task_id: recommendTaskId,
        provider_ids: selectedProviders,
      });
      const data = res?.data || res;
      message.success(data?.message || '推荐成功');
      setRecommendModal(false);
      loadTasks();
    } catch {
      message.error('推荐失败');
    } finally {
      setRecommending(false);
    }
  };

  const filteredTasks = searchText
    ? tasks.filter(
        (t) =>
          t.name.toLowerCase().includes(searchText.toLowerCase()) ||
          t.publisher.toLowerCase().includes(searchText.toLowerCase())
      )
    : tasks;

  const stats = {
    total: tasks.length,
    pending: tasks.filter((t) => t.status === 'pending').length,
    training: tasks.filter((t) => t.status === 'training').length,
    completed: tasks.filter((t) => ['completed', 'settled'].includes(t.status)).length,
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (name: string, record: TaskItem) => (
        <a onClick={() => navigate(`/app/tasks/${record.id}`)}>{name}</a>
      ),
    },
    {
      title: '发布者',
      dataIndex: 'publisher',
      key: 'publisher',
      width: 100,
    },
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
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
      width: 160,
      render: (_: any, record: TaskItem) => {
        const pct = record.maxRounds > 0 ? Math.round((record.currentRound / record.maxRounds) * 100) : 0;
        return (
          <div>
            <Progress percent={pct} size="small" />
            <span style={{ fontSize: 12, color: '#999' }}>{record.currentRound}/{record.maxRounds}</span>
          </div>
        );
      },
    },
    {
      title: '奖励池',
      dataIndex: 'rewardPool',
      key: 'rewardPool',
      width: 120,
      render: (v: number) => <span style={{ color: '#fa8c16' }}>¥{(v || 0).toLocaleString()}</span>,
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 120,
      render: (t: string) => t ? new Date(t).toLocaleDateString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      render: (_: any, record: TaskItem) => (
        <Space size="small">
          <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/app/tasks/${record.id}`)}>
            详情
          </Button>
          {(record.status === 'pending' || record.status === 'matching') && (
            <Button size="small" icon={<SendOutlined />} onClick={() => openRecommendModal(record.id)}>
              推荐
            </Button>
          )}
          <Popconfirm
            title="确认删除"
            description={`确认删除任务「${record.name}」？此操作不可恢复。`}
            onConfirm={() => handleDelete(record.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className={styles.taskManagement}>
      <div className={styles.pageHeader}>
        <h1>任务管理</h1>
        <p>管理平台所有任务</p>
      </div>

      <Row gutter={[24, 24]} className={styles.statsRow}>
        <Col xs={12} sm={6}>
          <Card><Statistic title="总任务数" value={stats.total} prefix={<ProjectOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="待开始" value={stats.pending} valueStyle={{ color: '#faad14' }} prefix={<ClockCircleOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="训练中" value={stats.training} valueStyle={{ color: '#1890ff' }} prefix={<PlayCircleOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="已完成" value={stats.completed} valueStyle={{ color: '#52c41a' }} prefix={<CheckCircleOutlined />} /></Card>
        </Col>
      </Row>

      <Card className={styles.filterCard}>
        <Space wrap>
          <Input
            placeholder="搜索任务名称/发布者"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            allowClear
            style={{ width: 220, minWidth: 140, maxWidth: '100%' }}
          />
          <Select value={statusFilter} onChange={setStatusFilter} style={{ width: 140, minWidth: 100 }}>
            <Option value="all">全部状态</Option>
            <Option value="pending">待开始</Option>
            <Option value="training">训练中</Option>
            <Option value="completed">已完成</Option>
            <Option value="settled">已结算</Option>
          </Select>
          <Button icon={<ReloadOutlined />} onClick={loadTasks}>刷新</Button>
        </Space>
      </Card>

      <Card className={styles.tableCard}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
        ) : (
          <Table
            columns={columns}
            dataSource={filteredTasks}
            rowKey="id"
            scroll={{ x: 900 }}
            pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 条` }}
          />
        )}
      </Card>

      <Modal
        title="推荐任务给数据提供方"
        open={recommendModal}
        onOk={handleRecommend}
        onCancel={() => setRecommendModal(false)}
        confirmLoading={recommending}
        okText="确认推荐"
        cancelText="取消"
      >
        <p style={{ marginBottom: 12, color: '#666' }}>选择要推荐此任务的数据提供方：</p>
        <Checkbox.Group
          value={selectedProviders}
          onChange={(vals) => setSelectedProviders(vals as string[])}
          style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
        >
          {providers.map((p) => (
            <Checkbox key={p.id} value={p.id} disabled={!p.hasNode}>
              <span style={{ fontWeight: 500 }}>{p.username}</span>
              <span style={{ color: '#999', marginLeft: 8 }}>
                {p.email} {p.hasNode ? `(节点: ${p.nodeName})` : '(无节点)'}
              </span>
            </Checkbox>
          ))}
          {providers.length === 0 && <span style={{ color: '#999' }}>暂无数据提供方</span>}
        </Checkbox.Group>
      </Modal>
    </div>
  );
};

export default TaskManagement;
