import React, { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Button,
  Progress,
  Timeline,
  Tag,
  Space,
  Modal,
  Form,
  InputNumber,
  Select,
  message,
  Descriptions,
  Divider,
  List,
  Avatar,
} from 'antd';
import {
  WalletOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  UserOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import {
  SettlementSummary,
  NodeContribution,
  RevenueShareRecord,
} from '../../../../types/training';

interface SettlementPanelProps {
  summary: SettlementSummary;
  contributions: NodeContribution[];
  shareRecords: RevenueShareRecord[];
}

const SettlementPanel: React.FC<SettlementPanelProps> = ({
  summary,
  contributions,
  shareRecords,
}) => {
  const [settlementModalVisible, setSettlementModalVisible] = useState(false);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [form] = Form.useForm();

  // 待结算记录
  const pendingRecords = shareRecords.filter((r) => r.status === 'pending');

  // 计算统计数据
  const completedAmount = shareRecords
    .filter((r) => r.status === 'completed')
    .reduce((sum, r) => sum + r.amount, 0);

  const pendingAmount = pendingRecords.reduce((sum, r) => sum + r.amount, 0);

  // 结算处理
  const handleSettlement = (values: any) => {
    console.log('Settlement values:', values);
    message.success('结算请求已提交，正在处理中...');
    setSettlementModalVisible(false);
    form.resetFields();
  };

  // 批量结算
  const handleBatchSettlement = () => {
    Modal.confirm({
      title: '确认批量结算',
      icon: <ExclamationCircleOutlined />,
      content: `将对 ${pendingRecords.length} 条待处理记录进行结算，总金额 ${pendingAmount} CNY`,
      onOk() {
        message.success('批量结算请求已提交');
      },
    });
  };

  return (
    <div>
      <Row gutter={[16, 16]}>
        {/* 左侧：结算概览 */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <WalletOutlined />
                <span>结算概览</span>
              </Space>
            }
            extra={
              <Tag color="blue">
                已完成 {summary.completedRounds} 轮
              </Tag>
            }
          >
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="总奖励池">
                <span className="font-bold text-blue-600">
                  ¥{summary.totalReward.toLocaleString()}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="已分配">
                <span className="font-bold text-green-600">
                  ¥{completedAmount.toLocaleString()}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="待分配">
                <span className="font-bold text-orange-500">
                  ¥{summary.pendingReward.toLocaleString()}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="分配进度">
                <Progress
                  percent={Math.round(
                    (summary.distributedReward / summary.totalReward) * 100
                  )}
                  size="small"
                  status="active"
                />
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <div className="flex justify-between items-center">
              <div>
                <div className="text-gray-500 mb-1">待结算金额</div>
                <div className="text-2xl font-bold text-orange-500">
                  ¥{pendingAmount.toLocaleString()}
                </div>
              </div>
              <Button
                type="primary"
                icon={<DollarOutlined />}
                size="large"
                onClick={handleBatchSettlement}
                disabled={pendingRecords.length === 0}
              >
                批量结算
              </Button>
            </div>
          </Card>

          {/* 结算时间线 */}
          <Card
            title={
              <Space>
                <ClockCircleOutlined />
                <span>结算历史</span>
              </Space>
            }
            className="mt-4"
          >
            <Timeline mode="left">
              {shareRecords
                .filter((r) => r.status === 'completed')
                .slice(0, 5)
                .map((record) => (
                  <Timeline.Item
                    key={record.id}
                    label={record.settledAt ? new Date(record.settledAt).toLocaleDateString() : '-'}
                    color="green"
                  >
                    <div className="text-sm">
                      <div className="font-medium">{record.nodeName}</div>
                      <div className="text-gray-500">
                        第 {record.round} 轮 - ¥{record.amount.toLocaleString()}
                      </div>
                    </div>
                  </Timeline.Item>
                ))}
            </Timeline>
          </Card>
        </Col>

        {/* 右侧：节点结算详情 */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <UserOutlined />
                <span>节点结算详情</span>
              </Space>
            }
            extra={
              <Select
                placeholder="选择节点"
                style={{ width: 150 }}
                onChange={(value) => setSelectedNode(value)}
                allowClear
              >
                {contributions.map((node) => (
                  <Select.Option key={node.nodeId} value={node.nodeId}>
                    {node.nodeName}
                  </Select.Option>
                ))}
              </Select>
            }
          >
            <List
              itemLayout="horizontal"
              dataSource={
                selectedNode
                  ? contributions.filter((n) => n.nodeId === selectedNode)
                  : contributions
              }
              renderItem={(node) => {
                const nodeRecords = shareRecords.filter(
                  (r) => r.nodeId === node.nodeId
                );
                const nodePending = nodeRecords.filter(
                  (r) => r.status === 'pending'
                );
                const nodeCompleted = nodeRecords.filter(
                  (r) => r.status === 'completed'
                );

                return (
                  <List.Item
                    actions={[
                      <Button
                        type="link"
                        icon={<DollarOutlined />}
                        onClick={() => {
                          setSelectedNode(node.nodeId);
                          setSettlementModalVisible(true);
                        }}
                        disabled={nodePending.length === 0}
                      >
                        结算
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      avatar={
                        <Avatar
                          size="large"
                          style={{ backgroundColor: '#1890ff' }}
                        >
                          {node.nodeName.charAt(0)}
                        </Avatar>
                      }
                      title={
                        <Space>
                          <span>{node.nodeName}</span>
                          <Tag color="blue">
                            贡献度 {node.overallScore.toFixed(1)}
                          </Tag>
                        </Space>
                      }
                      description={
                        <div className="text-sm mt-1">
                          <div className="flex gap-4">
                            <span>
                              已获得: ¥
                              {nodeCompleted
                                .reduce((sum, r) => sum + r.amount, 0)
                                .toLocaleString()}
                            </span>
                            <span className="text-orange-500">
                              待结算: ¥
                              {nodePending
                                .reduce((sum, r) => sum + r.amount, 0)
                                .toLocaleString()}
                            </span>
                          </div>
                          <div className="text-gray-500 mt-1">
                            参与轮次: {node.roundsParticipated} | 数据样本:{' '}
                            {node.sampleCount.toLocaleString()}
                          </div>
                        </div>
                      }
                    />
                  </List.Item>
                );
              }}
            />
          </Card>

          {/* 结算规则说明 */}
          <Card
            title="结算规则"
            className="mt-4"
            type="inner"
          >
            <Descriptions column={1} size="small">
              <Descriptions.Item label="计算周期">
                每完成一轮联邦训练后自动计算
              </Descriptions.Item>
              <Descriptions.Item label="分账公式">
                节点奖励 = 总奖励池 × (节点贡献度 / 总贡献度)
              </Descriptions.Item>
              <Descriptions.Item label="贡献度计算">
                数据质量(25%) + 数据量(25%) + 计算能力(30%) + 及时性(20%)
              </Descriptions.Item>
              <Descriptions.Item label="结算方式">
                支持自动结算和手动结算两种方式
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      {/* 结算模态框 */}
      <Modal
        title="手动结算"
        open={settlementModalVisible}
        onCancel={() => setSettlementModalVisible(false)}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSettlement}
          initialValues={{
            settlementType: 'full',
          }}
        >
          <Form.Item
            name="nodeId"
            label="结算节点"
            rules={[{ required: true, message: '请选择结算节点' }]}
            initialValue={selectedNode || undefined}
          >
            <Select placeholder="选择节点">
              {contributions.map((node) => (
                <Select.Option key={node.nodeId} value={node.nodeId}>
                  {node.nodeName} (待结算: ¥
                  {shareRecords
                    .filter(
                      (r) =>
                        r.nodeId === node.nodeId && r.status === 'pending'
                    )
                    .reduce((sum, r) => sum + r.amount, 0)
                    .toLocaleString()}
                  )
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="settlementType"
            label="结算类型"
            rules={[{ required: true }]}
          >
            <Select>
              <Select.Option value="full">全额结算</Select.Option>
              <Select.Option value="partial">部分结算</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prev, curr) =>
              prev.settlementType !== curr.settlementType
            }
          >
            {({ getFieldValue }) =>
              getFieldValue('settlementType') === 'partial' ? (
                <Form.Item
                  name="amount"
                  label="结算金额"
                  rules={[
                    { required: true, message: '请输入结算金额' },
                    {
                      type: 'number',
                      min: 1,
                      message: '金额必须大于0',
                    },
                  ]}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    prefix="¥"
                    placeholder="输入结算金额"
                  />
                </Form.Item>
              ) : null
            }
          </Form.Item>

          <Form.Item>
            <Space className="w-full justify-end">
              <Button onClick={() => setSettlementModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" icon={<CheckCircleOutlined />}>
                确认结算
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SettlementPanel;
