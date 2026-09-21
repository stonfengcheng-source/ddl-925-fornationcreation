/**
 * TaskDetail 页面
 * 任务详情展示 - 包含任务基本信息、配置参数、奖励信息
 * 路径: /tasks/:taskId
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Layout,
  Row,
  Col,
  Spin,
  Button,
  Breadcrumb,
  Card,
  Tag,
  Statistic,
  Progress,
  Timeline,
  Tabs,
  Descriptions,
  Alert,
  Divider,
  Empty,
  message,
} from 'antd';
import {
  ArrowLeftOutlined,
  ShareAltOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  TeamOutlined,
  TrophyOutlined,
  DollarOutlined,
  SettingOutlined,
  FileTextOutlined,
  SafetyOutlined,
  EyeOutlined,
  DatabaseOutlined,
  ReloadOutlined,
  PieChartOutlined,
} from '@ant-design/icons';
import request from '@/services/request';

// 预评估面板
import PreEstimatePanel from './components/PreEstimatePanel';

// 语义匹配相关导入
import type { MatchingDataset } from '@/types/training';
import { getMatchingDatasetsForTask } from '@/services/api/semanticMatching';
import MatchingDatasetCard from '@/components/MatchingDatasetCard';

import styles from './index.module.less';

const { Content } = Layout;
const { TabPane } = Tabs;

interface TaskData {
  id: string;
  task_name: string;
  task_category: string;
  task_description: string;
  task_tags: string[];
  status: string;
  min_data_size: number | null;
  min_nodes: number | null;
  max_nodes: number | null;
  data_formats: string[] | null;
  privacy_level: string | null;
  model_type: string | null;
  optimizer: string | null;
  learning_rate: number | null;
  batch_size: number | null;
  local_epochs: number | null;
  aggregation_strategy: string | null;
  target_accuracy: number | null;
  max_rounds: number | null;
  current_round: number;
  current_accuracy: number | null;
  reward_pool: number | null;
  reward_currency: string;
  progress: number;
  participant_count: number;
  publisher_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

// 状态标签组件
const StatusTag = ({ status }: { status: string }) => {
  const config: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
    pending: { color: 'default', icon: <ClockCircleOutlined />, text: '待开始' },
    training: { color: 'processing', icon: <SyncOutlined spin />, text: '训练中' },
    running: { color: 'processing', icon: <SyncOutlined spin />, text: '运行中' },
    paused: { color: 'warning', icon: <PauseCircleOutlined />, text: '已暂停' },
    completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
    failed: { color: 'error', icon: <CloseCircleOutlined />, text: '失败' },
    cancelled: { color: 'default', icon: <CloseCircleOutlined />, text: '已取消' },
  };
  const { color, icon, text } = config[status] || config.pending;
  return (
    <Tag icon={icon} color={color} className="text-base px-3 py-1">
      {text}
    </Tag>
  );
};

const TaskDetail: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [task, setTask] = useState<TaskData | null>(null);
  const [activeTab, setActiveTab] = useState('overview');

  // 语义匹配数据集状态
  const [matchingDatasets, setMatchingDatasets] = useState<MatchingDataset[]>([]);
  const [loadingMatching, setLoadingMatching] = useState(false);

  // 获取语义匹配的数据集
  const fetchMatchingDatasets = async () => {
    if (!taskId) return;
    setLoadingMatching(true);
    try {
      const res = await getMatchingDatasetsForTask(taskId, 10, 0.3);
      setMatchingDatasets(res.data?.matches || []);
    } catch (error) {
      console.error('获取匹配数据集失败:', error);
    } finally {
      setLoadingMatching(false);
    }
  };

  useEffect(() => {
    if (!taskId) return;
    setLoading(true);
    request
      .get(`/tasks/${taskId}`)
      .then((res: any) => {
        setTask(res.data);
      })
      .catch((err: any) => {
        console.error('获取任务详情失败:', err);
      })
      .finally(() => {
        setLoading(false);
      });

    // 获取语义匹配的数据集
    fetchMatchingDatasets();
  }, [taskId]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen bg-gray-50">
        <Spin size="large" tip="加载任务详情..." />
      </div>
    );
  }

  if (!task) {
    return (
      <Content className="p-6">
        <Empty description="任务不存在" />
      </Content>
    );
  }

  const totalRounds = task.max_rounds || 100;
  const progressPercent = totalRounds > 0 ? Math.round((task.current_round / totalRounds) * 100) : 0;

  return (
    <Content className={styles.taskDetail}>
      {/* 面包屑导航 */}
      <Breadcrumb
        items={[
          { title: '首页', onClick: () => navigate('/app/dashboard') },
          { title: '任务大厅', onClick: () => navigate('/app/tasks') },
          { title: task.task_name },
        ]}
        className="mb-4"
      />

      {/* 页面头部 */}
      <div className={styles.pageHeader}>
        <div className={styles.headerContent}>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate(-1)}
            className={styles.backButton}
          />
          <div className={styles.titleSection}>
            <h1>{task.task_name}</h1>
            <div className={styles.taskMeta}>
              <span>ID: {task.id?.substring(0, 8)}</span>
              {task.created_at && (
                <span>创建时间: {new Date(task.created_at).toLocaleDateString()}</span>
              )}
              <span>类别: {task.task_category}</span>
            </div>
            <div className={styles.tagList}>
              {(task.task_tags || []).map((tag) => (
                <Tag key={tag} className={styles.tag}>
                  {tag}
                </Tag>
              ))}
            </div>
          </div>
          <div className={styles.headerActions}>
            <Button icon={<ShareAltOutlined />}>分享</Button>
            <Button
              icon={<PlayCircleOutlined />}
              type="primary"
              onClick={() => navigate(`/app/federated/training/${task.id}`)}
            >
              {task.status === 'training' || task.status === 'running' ? '查看训练' : '进入训练'}
            </Button>
          </div>
        </div>
      </div>

      {/* 状态标签 */}
      <div className="mb-6">
        <StatusTag status={task.status} />
      </div>

      <div className={styles.contentLayout}>
        {/* 左侧主要内容 */}
        <div className={styles.mainContent}>
          {/* 进度概览 */}
          <Card className={styles.progressSection}>
            <div className={styles.progressHeader}>
              <h3>训练进度</h3>
              <span className={styles.progressText}>
                第 {task.current_round} / {totalRounds} 轮 ({progressPercent}%)
              </span>
            </div>
            <Progress
              percent={progressPercent}
              strokeColor={{ from: '#108ee9', to: '#87d068' }}
              strokeWidth={12}
              showInfo={false}
            />
            <Row gutter={16} className={styles.progressStats}>
              <Col span={12}>
                <Statistic
                  title="当前准确率"
                  value={task.current_accuracy || 0}
                  precision={3}
                  prefix={<TrophyOutlined />}
                  suffix={task.target_accuracy ? `/ ${(task.target_accuracy * 100).toFixed(0)}%` : ''}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="参与节点数"
                  value={task.participant_count}
                  prefix={<TeamOutlined />}
                />
              </Col>
            </Row>
          </Card>

          {/* 标签页内容 */}
          <Card className={styles.sectionCard}>
            <Tabs activeKey={activeTab} onChange={setActiveTab}>
              <TabPane
                tab={
                  <span>
                    <FileTextOutlined />
                    任务概览
                  </span>
                }
                key="overview"
              >
                <Descriptions title="任务描述" column={1} className="mb-6">
                  <Descriptions.Item>{task.task_description}</Descriptions.Item>
                </Descriptions>

                <Divider />

                <Descriptions title="数据要求" column={2}>
                  <Descriptions.Item label="最小数据量">
                    {(task.min_data_size || 0).toLocaleString()} 条
                  </Descriptions.Item>
                  <Descriptions.Item label="节点数量">
                    {task.min_nodes || '-'} - {task.max_nodes || '-'} 个
                  </Descriptions.Item>
                  <Descriptions.Item label="数据格式">
                    {(task.data_formats || []).join(', ') || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="隐私等级">
                    {task.privacy_level || '-'}
                  </Descriptions.Item>
                </Descriptions>
              </TabPane>

              <TabPane
                tab={
                  <span>
                    <SettingOutlined />
                    配置参数
                  </span>
                }
                key="config"
              >
                <Descriptions bordered column={2} className={styles.configTable}>
                  <Descriptions.Item label="模型类型">{task.model_type || '-'}</Descriptions.Item>
                  <Descriptions.Item label="优化器">{task.optimizer || '-'}</Descriptions.Item>
                  <Descriptions.Item label="学习率">{task.learning_rate ?? '-'}</Descriptions.Item>
                  <Descriptions.Item label="批次大小">{task.batch_size ?? '-'}</Descriptions.Item>
                  <Descriptions.Item label="本地轮次">{task.local_epochs ?? '-'}</Descriptions.Item>
                  <Descriptions.Item label="聚合策略">
                    {task.aggregation_strategy?.toUpperCase() || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="目标准确率">
                    {task.target_accuracy ? `${(task.target_accuracy * 100).toFixed(0)}%` : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="最大轮次">{task.max_rounds ?? '-'}</Descriptions.Item>
                </Descriptions>
              </TabPane>

              <TabPane
                tab={
                  <span>
                    <TeamOutlined />
                    参与方
                  </span>
                }
                key="participants"
              >
                <Empty description="暂无参与节点，等待节点加入训练" />
              </TabPane>

              {/* 预评估Tab - 仅在pending或matching状态显示 */}
              {(task.status === 'pending' || task.status === 'matching') && (
                <TabPane
                  tab={
                    <span>
                      <PieChartOutlined />
                      预评估
                    </span>
                  }
                  key="pre-estimate"
                >
                  <PreEstimatePanel
                    taskId={task.id}
                    rewardPool={task.reward_pool || 0}
                    onStartTraining={() => navigate(`/app/federated/training/${task.id}`)}
                  />
                </TabPane>
              )}

              <TabPane
                tab={
                  <span>
                    <DatabaseOutlined />
                    匹配的数据集
                    {matchingDatasets.length > 0 && (
                      <span style={{ marginLeft: 4, color: '#1890ff' }}>
                        ({matchingDatasets.length})
                      </span>
                    )}
                  </span>
                }
                key="matching-datasets"
              >
                {loadingMatching ? (
                  <Row gutter={[16, 16]}>
                    {[1, 2, 3].map((i) => (
                      <Col xs={24} md={12} key={i}>
                        <Card loading bodyStyle={{ padding: '16px' }} />
                      </Col>
                    ))}
                  </Row>
                ) : matchingDatasets.length > 0 ? (
                  <>
                    <Alert
                      message="AI 智能匹配"
                      description="以下数据集是基于语义相似度、标签匹配度和数据量匹配度综合计算的结果，帮助您快速找到合适的参与方。"
                      type="info"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                    <Row gutter={[16, 16]}>
                      {matchingDatasets.map((dataset) => (
                        <Col xs={24} md={12} key={dataset.dataset_id}>
                          <MatchingDatasetCard
                            dataset={dataset}
                            onViewDetail={(id) => navigate(`/app/data-assets/${id}`)}
                            onInvite={(id) => {
                              message.success(`已发送邀请给数据集 ${id.substring(0, 8)}... 的拥有者`);
                            }}
                          />
                        </Col>
                      ))}
                    </Row>
                  </>
                ) : (
                  <Empty
                    description={
                      <span>
                        暂无匹配的数据集
                        <br />
                        <small style={{ color: '#999' }}>
                          系统会根据任务描述自动匹配相关数据集，请稍后再试
                        </small>
                      </span>
                    }
                  >
                    <Button
                      type="primary"
                      icon={<ReloadOutlined />}
                      onClick={fetchMatchingDatasets}
                      loading={loadingMatching}
                    >
                      重新匹配
                    </Button>
                  </Empty>
                )}
              </TabPane>
            </Tabs>
          </Card>
        </div>

        {/* 右侧边栏 */}
        <div className={styles.sideContent}>
          {/* 隐私预算预估卡片 */}
          <Card
            className={styles.sectionCard}
            title={
              <span className="flex items-center gap-2">
                <SafetyOutlined style={{ color: '#fa8c16' }} />
                隐私保护配置
              </span>
            }
          >
            {(() => {
              // 根据隐私等级计算预估预算
              const privacyLevel = task.privacy_level?.toLowerCase() || 'medium';
              const totalRounds = task.max_rounds || 100;
              const epsilonPerRound =
                privacyLevel === 'high' ? 0.005 :
                privacyLevel === 'low' ? 0.02 : 0.01;
              const totalEpsilon = epsilonPerRound * totalRounds;
              const consumedRounds = task.current_round || 0;
              const consumedEpsilon = consumedRounds * epsilonPerRound;
              const remainingEpsilon = Math.max(0, totalEpsilon - consumedEpsilon);
              const remainingRounds = Math.floor(remainingEpsilon / epsilonPerRound);

              return (
                <>
                  <Row gutter={[16, 16]} className="mb-4">
                    <Col span={8}>
                      <div className="text-center">
                        <div className="text-xs text-gray-500 mb-1">隐私等级</div>
                        <Tag
                          color={
                            privacyLevel === 'high' ? 'green' :
                            privacyLevel === 'low' ? 'orange' : 'blue'
                          }
                          className="font-medium"
                        >
                          {privacyLevel === 'high' ? '高' :
                           privacyLevel === 'low' ? '低' : '中'}
                        </Tag>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div className="text-center">
                        <div className="text-xs text-gray-500 mb-1">总预算</div>
                        <div className="font-mono font-medium" style={{ color: '#fa8c16' }}>
                          ε = {totalEpsilon.toFixed(2)}
                        </div>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div className="text-center">
                        <div className="text-xs text-gray-500 mb-1">预估轮次</div>
                        <div className="font-mono font-medium">
                          ~{totalRounds}轮
                        </div>
                      </div>
                    </Col>
                  </Row>

                  <div className="text-sm text-gray-600 mb-3">
                    <div className="flex justify-between mb-2">
                      <span>每轮消耗:</span>
                      <span className="font-mono">ε ≈ {epsilonPerRound.toFixed(3)}</span>
                    </div>
                    {consumedRounds > 0 && (
                      <>
                        <div className="flex justify-between mb-2">
                          <span>已消耗:</span>
                          <span className="font-mono" style={{ color: '#fa8c16' }}>
                            ε = {consumedEpsilon.toFixed(3)}
                          </span>
                        </div>
                        <div className="flex justify-between mb-2">
                          <span>剩余预算:</span>
                          <span
                            className="font-mono"
                            style={{
                              color: remainingEpsilon < totalEpsilon * 0.2 ? '#f5222d' : '#52c41a'
                            }}
                          >
                            ε = {remainingEpsilon.toFixed(3)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>预计剩余轮次:</span>
                          <span className="font-medium">~{remainingRounds}轮</span>
                        </div>
                      </>
                    )}
                  </div>

                  <Button
                    type="link"
                    icon={<EyeOutlined />}
                    onClick={() => navigate('/app/privacy-budget')}
                    className="px-0"
                  >
                    查看详细预算
                  </Button>
                </>
              );
            })()}
          </Card>

          {/* 奖励信息 */}
          <Card className={styles.sectionCard}>
            <Statistic
              title="奖励池总额"
              value={task.reward_pool || 0}
              prefix={<DollarOutlined />}
              suffix={task.reward_currency}
              valueStyle={{ color: '#fa8c16', fontSize: 28 }}
            />
            <Divider />
            <div className="text-sm text-gray-500">
              <div className="flex justify-between mb-2">
                <span>已分配:</span>
                <span className="text-green-600 font-medium">
                  ¥0
                </span>
              </div>
              <div className="flex justify-between">
                <span>待分配:</span>
                <span className="text-orange-500 font-medium">
                  ¥{(task.reward_pool || 0).toLocaleString()}
                </span>
              </div>
            </div>
          </Card>

          {/* 状态时间线 */}
          <Card className={`${styles.sectionCard} ${styles.timelineCard}`} title="任务时间线">
            <Timeline mode="left">
              <Timeline.Item color="green">
                <h4>任务创建</h4>
                <p>任务已创建并发布到平台</p>
                {task.created_at && (
                  <div className={styles.timelineTime}>
                    {new Date(task.created_at).toLocaleString()}
                  </div>
                )}
              </Timeline.Item>
              {task.status !== 'pending' && (
                <Timeline.Item color="blue">
                  <h4>等待节点加入</h4>
                  <p>任务等待足够节点加入训练</p>
                </Timeline.Item>
              )}
            </Timeline>
          </Card>

          {/* 操作提示 */}
          <Alert
            message="需要帮助？"
            description="如有任何问题，请联系平台客服或查看帮助文档。"
            type="info"
            showIcon
            action={
              <Button size="small" type="primary">
                联系客服
              </Button>
            }
          />
        </div>
      </div>
    </Content>
  );
};

export default TaskDetail;
