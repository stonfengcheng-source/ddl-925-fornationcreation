import React, { useState, useEffect } from 'react';
import request from '@/services/request';
import {
  Card,
  Statistic,
  Table,
  Tag,
  Space,
  Spin,
  Row,
  Col,
  Empty,
} from 'antd';
import {
  WalletOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import './index.less';

interface WalletData {
  balance: number;
  pending_amount: number;
  total_earned: number;
  currency: string;
}

interface Transaction {
  id: string;
  task_id: string;
  task_name: string;
  node_name: string;
  amount: number;
  currency: string;
  share_percentage: number;
  status: string;
  created_at: string;
}

const Wallet: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [wallet, setWallet] = useState<WalletData | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [balRes, txRes]: any[] = await Promise.all([
        request.get('/wallet/balance'),
        request.get('/wallet/transactions'),
      ]);
      setWallet(balRes?.data || balRes || null);
      const txns = txRes?.data?.transactions || txRes?.transactions || [];
      setTransactions(Array.isArray(txns) ? txns : []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'task_name',
      key: 'task_name',
      ellipsis: true,
    },
    {
      title: '节点',
      dataIndex: 'node_name',
      key: 'node_name',
    },
    {
      title: '贡献占比',
      dataIndex: 'share_percentage',
      key: 'share_percentage',
      width: 100,
      render: (v: number) => `${(v || 0).toFixed(1)}%`,
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      width: 150,
      render: (amount: number, record: Transaction) => (
        <span className="font-mono font-semibold" style={{ color: '#3f8600' }}>
          +¥{(amount || 0).toLocaleString()} {record.currency}
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const m: Record<string, { color: string; text: string }> = {
          settled: { color: 'success', text: '已到账' },
          pending: { color: 'warning', text: '待结算' },
        };
        const cfg = m[status] || m.pending;
        return <Tag color={cfg.color}>{cfg.text}</Tag>;
      },
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
  ];

  if (loading) {
    return (
      <div className="flex justify-center items-center" style={{ minHeight: 400 }}>
        <Spin size="large" tip="加载钱包数据..." />
      </div>
    );
  }

  return (
    <div className="profile-page">
      {/* 余额卡片 */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={24} align="middle">
          <Col xs={24} md={8}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <WalletOutlined style={{ fontSize: 48, color: '#1890ff' }} />
              <div>
                <div style={{ color: 'rgba(0,0,0,0.45)', marginBottom: 8 }}>账户余额</div>
                <div style={{ fontSize: 32, fontWeight: 600 }}>
                  ¥{(wallet?.balance || 0).toFixed(2)}
                </div>
              </div>
            </div>
          </Col>
          <Col xs={24} md={8}>
            <Statistic
              title={<Space><ClockCircleOutlined /> 待结算金额</Space>}
              value={wallet?.pending_amount || 0}
              precision={2}
              prefix="¥"
              valueStyle={{ color: '#faad14' }}
            />
          </Col>
          <Col xs={24} md={8}>
            <Statistic
              title={<Space><CheckCircleOutlined /> 累计收入</Space>}
              value={wallet?.total_earned || 0}
              precision={2}
              prefix="¥"
              valueStyle={{ color: '#3f8600' }}
            />
          </Col>
        </Row>
      </Card>

      {/* 收益记录 */}
      <Card
        title={<Space><HistoryOutlined /><span>收益记录</span></Space>}
        extra={<Tag color="blue">{transactions.length} 条记录</Tag>}
      >
        {transactions.length > 0 ? (
          <Table
            columns={columns}
            dataSource={transactions}
            rowKey="id"
            pagination={{
              pageSize: 10,
              showTotal: (total) => `共 ${total} 条记录`,
            }}
          />
        ) : (
          <Empty description="暂无收益记录，参与联邦学习任务后收益将在此显示" />
        )}
      </Card>
    </div>
  );
};

export default Wallet;
