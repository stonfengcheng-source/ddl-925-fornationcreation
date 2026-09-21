import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import request from '@/services/request';

interface TaskDataType {
  key: string;
  title: string;
  description: string;
  budget: number;
  currency: string;
  status: 'pending' | 'training' | 'completed' | 'failed';
  tags: string[];
  category: string;
  created_at: string;
}


const TaskList: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<TaskDataType[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const res: any = await request.get('/tasks');
      const tasks = (res.data || []).map((t: any) => ({
        key: t.id,
        title: t.task_name,
        description: t.task_description || '',
        budget: t.reward_pool || 0,
        currency: t.reward_currency || 'CNY',
        status: t.status || 'pending',
        tags: t.task_tags || [],
        category: t.task_category || '',
        created_at: t.created_at || '',
      }));
      setData(tasks);
    } catch (error) {
      console.error('获取任务列表失败:', error);
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight gradient-text">任务大厅</h2>
          <p className="text-text-secondary mt-1">浏览可用的计算任务和联邦学习请求</p>
        </div>
        <Button effect="3d" className="shadow-lg" onClick={() => navigate('/app/tasks/publish')}>发布任务</Button>
      </div>

      {loading ? (
        <div className="text-center py-20 text-text-secondary">加载中...</div>
      ) : data.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-text-secondary text-lg">暂无任务</p>
          <p className="text-text-tertiary mt-2">点击右上角"发布任务"创建第一个联邦学习任务</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data.map((task, index) => (
            <Card 
              key={task.key} 
              hoverEffect 
              className="border-border/50 bg-white/80 backdrop-blur cursor-pointer"
              style={{ animationDelay: `${index * 100}ms` }}
              onClick={() => navigate(`/app/tasks/${task.key}`)}
            >
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start">
                  <CardTitle className="text-lg font-medium text-text group-hover:text-accent transition-colors">
                    {task.title}
                  </CardTitle>
                  <StatusBadge status={task.status} />
                </div>
                {task.category && (
                  <div className="mt-1 text-xs text-text-tertiary">{task.category}</div>
                )}
              </CardHeader>
              <CardContent>
                <div className="flex flex-col gap-4">
                  {task.description && (
                    <p className="text-sm text-text-secondary line-clamp-2">{task.description}</p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    {task.tags.map(tag => (
                      <span key={tag} className="px-2.5 py-0.5 rounded-full text-xs font-semibold border bg-text-secondary/10 text-text-secondary border-text-secondary/20">
                        #{tag}
                      </span>
                    ))}
                  </div>
                  
                  <div className="flex items-end justify-between mt-2 pt-4 border-t border-border/50">
                    <div>
                      <div className="text-xs text-text-tertiary uppercase tracking-wider font-semibold">奖励池</div>
                      <div className="text-xl font-mono font-medium text-text">
                        {task.currency === 'CNY' ? '¥' : '$'}{task.budget.toLocaleString()}
                      </div>
                    </div>
                    <Button variant="secondary" size="sm" className="hover:bg-accent hover:text-white hover:border-accent transition-all">
                      查看详情
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

// Helper component for status
const StatusBadge = ({ status }: { status: string }) => {
  const styleMap: Record<string, string> = {
    pending: 'bg-accent-yellow/10 text-accent-yellow border-accent-yellow/20',
    training: 'bg-accent-blue/10 text-accent-blue border-accent-blue/20 badge-pulse',
    completed: 'bg-accent-green/10 text-accent-green border-accent-green/20',
    failed: 'bg-red-500/10 text-red-500 border-red-500/20',
  };
  
  const labels: Record<string, string> = {
    pending: '待开始',
    training: '训练中',
    completed: '已完成',
    failed: '已失败',
  };
  
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${styleMap[status] || styleMap.pending}`}>
      {labels[status] || '未知'}
    </span>
  );
};

export default TaskList;
