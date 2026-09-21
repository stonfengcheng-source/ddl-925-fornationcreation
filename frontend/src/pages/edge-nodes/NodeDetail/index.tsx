import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import request from '@/services/request'
import { Card, Descriptions, Button, Tag, Space, Layout, Spin, message, Modal } from 'antd'
import {
  ArrowLeftOutlined,
  DeleteOutlined,
} from '@ant-design/icons'

const { Content } = Layout

interface NodeDetailData {
  id: string
  node_name: string
  node_type: string
  ip_address: string | null
  port: number | null
  status: string
  location: string | null
  cpu_cores: number | null
  memory_total: string | null
  gpu_info: string | null
  disk_usage: number
  cpu_usage: number
  memory_usage: number
  last_heartbeat: string | null
  created_at: string | null
  owner_id: string | null
}

const statusMap: Record<string, { color: string; text: string }> = {
  online: { color: 'success', text: '在线' },
  offline: { color: 'default', text: '离线' },
}

const NodeDetailPage: React.FC = () => {
  const { nodeId } = useParams<{ nodeId: string }>()
  const navigate = useNavigate()
  const [node, setNode] = useState<NodeDetailData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchNodeDetail()
  }, [nodeId])

  const fetchNodeDetail = async () => {
    setLoading(true)
    try {
      const res: any = await request.get(`/nodes/${nodeId}`)
      setNode(res?.data || res)
    } catch {
      message.error('获取节点详情失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = () => {
    Modal.confirm({
      title: '确认删除节点',
      content: '确定要删除这个节点吗？此操作不可恢复。',
      okType: 'danger',
      onOk: async () => {
        try {
          await request.delete(`/nodes/${nodeId}`)
          message.success('节点已删除')
          navigate('/app/edge-nodes')
        } catch {
          message.error('删除失败')
        }
      },
    })
  }

  if (loading) {
    return (
      <Content>
        <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" tip="加载节点详情..." /></div>
      </Content>
    )
  }

  if (!node) {
    return (
      <Content>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/app/edge-nodes')} style={{ marginBottom: 16 }}>返回</Button>
        <div style={{ textAlign: 'center', padding: 80 }}>节点不存在或已被删除</div>
      </Content>
    )
  }

  const sCfg = statusMap[node.status] || statusMap.offline

  return (
    <Content>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/app/edge-nodes')}>返回</Button>
          <h1 style={{ margin: 0 }}>{node.node_name}</h1>
          <Tag color={sCfg.color}>{sCfg.text}</Tag>
        </Space>
        <Button danger icon={<DeleteOutlined />} onClick={handleDelete}>删除节点</Button>
      </div>

      <Card title="节点信息" style={{ marginBottom: 24 }}>
        <Descriptions bordered column={{ xs: 1, sm: 2 }}>
          <Descriptions.Item label="节点ID">{node.id}</Descriptions.Item>
          <Descriptions.Item label="节点名称">{node.node_name}</Descriptions.Item>
          <Descriptions.Item label="节点类型">{node.node_type}</Descriptions.Item>
          <Descriptions.Item label="IP地址">{node.ip_address ? `${node.ip_address}:${node.port}` : '-'}</Descriptions.Item>
          <Descriptions.Item label="位置">{node.location || '-'}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag color={sCfg.color}>{sCfg.text}</Tag></Descriptions.Item>
          <Descriptions.Item label="注册时间">{node.created_at ? new Date(node.created_at).toLocaleString() : '-'}</Descriptions.Item>
          <Descriptions.Item label="最后心跳">{node.last_heartbeat ? new Date(node.last_heartbeat).toLocaleString() : '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="硬件配置">
        <Descriptions bordered column={{ xs: 1, sm: 2 }}>
          <Descriptions.Item label="CPU核心数">{node.cpu_cores ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="内存总量">{node.memory_total || '-'}</Descriptions.Item>
          <Descriptions.Item label="磁盘使用率">{node.disk_usage ? `${node.disk_usage}%` : '-'}</Descriptions.Item>
          <Descriptions.Item label="GPU信息">{node.gpu_info || '-'}</Descriptions.Item>
          <Descriptions.Item label="CPU使用率">{node.cpu_usage ? `${node.cpu_usage}%` : '-'}</Descriptions.Item>
          <Descriptions.Item label="内存使用率">{node.memory_usage ? `${node.memory_usage}%` : '-'}</Descriptions.Item>
        </Descriptions>
      </Card>
    </Content>
  )
}

export default NodeDetailPage
