/**
 * 推荐任务页面（优化版）
 * 系统根据数据画像智能推荐匹配的联邦学习任务
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import request from '@/services/request';
import {
  Button,
  Tag,
  Empty,
  Typography,
  Badge,
  Progress,
  message,
} from 'antd';
import {
  StarOutlined,
  ThunderboltOutlined,
  DollarOutlined,
  EyeOutlined,
  InfoCircleOutlined,
  TeamOutlined,
  DatabaseOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { Card as UICard } from '@/components/ui/Card';

const { Title, Text, Paragraph } = Typography;

// 推荐任务接口（来自后端 /api/training/recommended）
interface MatchedTask {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  match_score: number;
  match_reasons: string[];
  min_samples: number;
  max_nodes: number;
  reward_pool: number;
  target_accuracy: number;
  current_participants: number;
  already_joined: boolean;
  status: string;
  created_at: string;
}

// 匹配度颜色
const getScoreColor = (score: number) => {
  if (score >= 0.9) return '#52c41a';
  if (score >= 0.8) return '#1890ff';
  if (score >= 0.7) return '#faad14';
  return '#ff4d4f';
};

const MatchingTasks: React.FC = () => {
  const navigate = useNavigate();
  const [joining, setJoining] = useState<string | null>(null);
  const [tasks, setTasks] = useState<MatchedTask[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecommended();
  }, []);

  const fetchRecommended = async () => {
    setLoading(true);
    try {
      const res: any = await request.get('/training/recommended');
      const list = res?.data || res || [];
      setTasks(Array.isArray(list) ? list : []);
    } catch {
      setTasks([]);
    } finally {
      setLoading(false);
    }
  };

  const handleJoin = async (taskId: string) => {
    setJoining(taskId);
    try {
      await request.post(`/training/${taskId}/join`);
      message.success('已成功参与任务！您的本地节点将在训练开始后自动参与。');
      fetchRecommended();
    } catch (error: any) {
      const detail = error?.response?.data?.detail || '加入失败，请重试';
      message.error(detail);
    } finally {
      setJoining(null);
    }
  };

  const viewDetail = (taskId: string) => {
    navigate(`/app/tasks/${taskId}`);
  };

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <Title level={3}>
          <StarOutlined className="mr-2 text-yellow-500" />
          推荐任务
        </Title>
        <Paragraph type="secondary">
          基于您的数据资产画像，为您匹配的科研协作机会
        </Paragraph>
      </div>

      {/* 说明 */}
      <div className="bg-blue-50 p-4 rounded-lg flex items-start gap-3">
        <InfoCircleOutlined className="text-blue-500 mt-1" />
        <div>
          <Text strong>智能匹配算法</Text>
          <Paragraph type="secondary" className="mb-0 text-sm">
            系统通过分析您的数据特征（类型、规模、质量）与科研项目需求的相似度进行推荐。
            匹配度越高，您的数据对项目的科研价值越大。
          </Paragraph>
        </div>
      </div>

      {/* 任务列表 */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">加载中...</div>
      ) : tasks.length > 0 ? (
        <div className="space-y-4">
          {tasks.map((task: MatchedTask, index: number) => (
            <UICard key={task.id} variant="default" hoverEffect>
              <div className="flex gap-6">
                {/* 左侧：匹配度 */}
                <div className="flex flex-col items-center justify-center w-24 shrink-0">
                  <div
                    className="text-3xl font-bold"
                    style={{ color: getScoreColor(task.match_score) }}
                  >
                    {Math.round(task.match_score * 100)}%
                  </div>
                  <Text type="secondary" className="text-xs">匹配度</Text>
                  <Badge
                    count={`#${index + 1}`}
                    style={{
                      backgroundColor: index < 3 ? '#1890ff' : '#999',
                      marginTop: 8,
                    }}
                  />
                </div>

                {/* 中间：任务信息 */}
                <div className="flex-1 min-w-0">
                  {/* 标题行 */}
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="text-lg font-semibold m-0">{task.name}</h3>
                    <Tag color="blue">{task.category}</Tag>
                    {task.already_joined && <Tag color="green">已参与</Tag>}
                  </div>

                  {/* 描述 */}
                  <Paragraph type="secondary" className="text-sm mb-3">
                    {task.description}
                  </Paragraph>

                  {/* 推荐理由 */}
                  <div className="bg-gray-50 p-2 rounded mb-3">
                    <Text type="secondary" className="text-xs block mb-1">
                      <InfoCircleOutlined className="mr-1" />
                      推荐理由：
                    </Text>
                    <ul className="list-disc list-inside text-xs text-gray-600 m-0">
                      {task.match_reasons.map((reason: string, idx: number) => (
                        <li key={idx}>{reason}</li>
                      ))}
                    </ul>
                  </div>

                  {/* 标签 */}
                  <div className="flex items-center gap-2 text-sm mb-2">
                    <DatabaseOutlined className="text-gray-400" />
                    <span className="text-gray-600">标签：</span>
                    {(task.tags || []).map((tag: string) => (
                      <Tag key={tag}>{tag}</Tag>
                    ))}
                    <span className="text-gray-400">≥{task.min_samples}例</span>
                  </div>

                  {/* 参与进度 */}
                  <div className="flex items-center gap-3">
                    <TeamOutlined className="text-gray-400" />
                    <span className="text-xs text-gray-600">
                      {task.current_participants}/{task.max_nodes} 个节点已参与
                    </span>
                    <Progress
                      percent={(task.current_participants / Math.max(task.max_nodes, 1)) * 100}
                      size="small"
                      style={{ width: 80 }}
                      showInfo={false}
                    />
                  </div>
                </div>

                {/* 右侧：数据面板 */}
                <div className="w-48 shrink-0 space-y-3">
                  {/* 奖金池 */}
                  <div className="bg-green-50 p-3 rounded">
                    <div className="flex items-center gap-2 text-green-600 mb-1">
                      <DollarOutlined />
                      <span className="text-xs">奖金池</span>
                    </div>
                    <div className="text-lg font-bold text-green-600">
                      ¥{(task.reward_pool || 0).toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">根据贡献度分配</div>
                  </div>

                  {/* 目标精度 */}
                  <div className="bg-blue-50 p-3 rounded">
                    <div className="flex items-center gap-2 text-blue-600 mb-1">
                      <ThunderboltOutlined />
                      <span className="text-xs">目标精度</span>
                    </div>
                    <div className="text-xl font-bold text-blue-600">
                      {((task.target_accuracy || 0) * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-gray-500">联邦学习目标</div>
                  </div>

                  {/* 操作按钮 */}
                  <div className="space-y-2 pt-2">
                    {task.already_joined ? (
                      <>
                        <Button
                          type="primary"
                          block
                          icon={<DownloadOutlined />}
                          onClick={async () => {
                            try {
                              const res = await fetch('/api/training/download-client');
                              const blob = await res.blob();
                              const url = window.URL.createObjectURL(blob);
                              const a = document.createElement('a');
                              a.href = url;
                              a.download = 'fl_client.zip';
                              document.body.appendChild(a);
                              a.click();
                              a.remove();
                              window.URL.revokeObjectURL(url);
                            } catch { message.error('下载失败'); }
                          }}
                        >
                          下载训练客户端
                        </Button>
                        <Button
                          block
                          onClick={() => navigate(`/app/federated/training/${task.id}`)}
                        >
                          查看训练
                        </Button>
                      </>
                    ) : (
                      <Button
                        type="primary"
                        block
                        onClick={() => handleJoin(task.id)}
                        loading={joining === task.id}
                      >
                        一键参与
                      </Button>
                    )}
                    <Button
                      block
                      icon={<EyeOutlined />}
                      onClick={() => viewDetail(task.id)}
                    >
                      查看详情
                    </Button>
                  </div>
                </div>
              </div>
            </UICard>
          ))}
        </div>
      ) : (
        <Empty
          description="暂无推荐任务"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Button type="primary" onClick={() => navigate('/app/data-assets/create')}>
            登记数据资产以获取推荐
          </Button>
        </Empty>
      )}
    </div>
  );
};

export default MatchingTasks;
