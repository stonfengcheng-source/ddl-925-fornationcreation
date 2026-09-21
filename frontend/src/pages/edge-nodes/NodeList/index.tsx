import { useState, useEffect } from 'react'
import request from '@/services/request'
import { Table, Button, Input, Select, Tag, Card, Row, Col, Statistic, Space, Empty, Layout, Spin } from 'antd'
import { useNavigate } from 'react-router-dom'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClusterOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons'

const { Content } = Layout
const { Option } = Select

interface NodeItem {
  id: string
  node_name: string
  node_type: string
  ip_address: string
  port: number
  status: string
  location: string
  cpu_cores: number | null
  memory_total: string | null
  cpu_usage: number | null
  memory_usage: number | null
  last_heartbeat: string | null
  created_at: string
}

const statusMap: Record<string, { color: string; text: string }> = {
  online: { color: 'success', text: '在线' },
  offline: { color: 'default', text: '离线' },
}

const NodeList: React.FC = () => {
  const navigate = useNavigate()
  const [nodes, setNodes] = useState<NodeItem[]>([])
  const [loading, setLoading] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')

  const fetchNodes = async () => {
    setLoading(true)
    try {
      const res: any = await request.get('/nodes/my')
      const list = res?.data || res || []
      setNodes(Array.isArray(list) ? list : [])
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchNodes()
  }, [])

  const filteredNodes = nodes.filter(node => {
    const matchesKeyword = !searchKeyword || node.node_name.toLowerCase().includes(searchKeyword.toLowerCase()) || (node.ip_address || '').includes(searchKeyword)
    const matchesStatus = !statusFilter || node.status === statusFilter
    return matchesKeyword && matchesStatus
  })

  const stats = {
    total: nodes.length,
    online: nodes.filter(n => n.status === 'online').length,
    offline: nodes.filter(n => n.status === 'offline').length,
  }

  const columns = [
    {
      title: '节点名称',
      dataIndex: 'node_name',
      key: 'node_name',
      ellipsis: true,
    },
    {
      title: 'IP地址',
      key: 'ip',
      width: 160,
      render: (_: any, r: NodeItem) => r.ip_address ? `${r.ip_address}:${r.port}` : '-',
    },
    {
      title: '类型',
      dataIndex: 'node_type',
      key: 'node_type',
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (s: string) => {
        const cfg = statusMap[s] || statusMap.offline
        return <Tag color={cfg.color}>{cfg.text}</Tag>
      },
    },
    {
      title: '位置',
      dataIndex: 'location',
      key: 'location',
      width: 120,
    },
    {
      title: 'CPU',
      key: 'cpu',
      width: 80,
      render: (_: any, r: NodeItem) => r.cpu_cores ? `${r.cpu_cores}核` : '-',
    },
    {
      title: '内存',
      key: 'mem',
      width: 80,
      render: (_: any, r: NodeItem) => r.memory_total || '-',
    },
    {
      title: '最后心跳',
      dataIndex: 'last_heartbeat',
      key: 'last_heartbeat',
      width: 160,
      render: (t: string | null) => t ? new Date(t).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: NodeItem) => (
        <Button type="link" size="small" onClick={() => navigate(`/app/edge-nodes/${record.id}`)}>
          详情
        </Button>
      ),
    },
  ]

  return (
    <Content>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>我的边缘节点</h1>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/app/edge-nodes/register')}>
          注册新节点
        </Button>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={8}>
          <Card><Statistic title="节点总数" value={stats.total} prefix={<ClusterOutlined />} /></Card>
        </Col>
        <Col xs={8}>
          <Card><Statistic title="在线" value={stats.online} valueStyle={{ color: '#52c41a' }} prefix={<CheckCircleOutlined />} /></Card>
        </Col>
        <Col xs={8}>
          <Card><Statistic title="离线" value={stats.offline} valueStyle={{ color: '#999' }} prefix={<CloseCircleOutlined />} /></Card>
        </Col>
      </Row>

      <Space style={{ marginBottom: 16 }} wrap>
        <Input
          placeholder="搜索节点名称或IP"
          prefix={<SearchOutlined />}
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          allowClear
          style={{ width: 220 }}
        />
        <Select placeholder="状态筛选" style={{ width: 120 }} onChange={(v) => setStatusFilter(v || '')} allowClear>
          <Option value="online">在线</Option>
          <Option value="offline">离线</Option>
        </Select>
        <Button icon={<ReloadOutlined />} onClick={fetchNodes}>刷新</Button>
      </Space>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
      ) : (
        <Table
          columns={columns}
          dataSource={filteredNodes}
          rowKey="id"
          pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 个节点` }}
          locale={{ emptyText: <Empty description="暂无节点，点击右上角注册新节点" /> }}
        />
      )}
    </Content>
  )
}

export default NodeList
