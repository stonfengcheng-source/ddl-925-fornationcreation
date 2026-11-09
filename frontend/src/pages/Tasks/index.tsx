import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { usePermission } from '@/hooks/usePermission';
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
  const { hasPermission, isProvider } = usePermission();
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
    <div className="space-y-7 fade-in">
      <header className="flex flex-col gap-5 rounded-2xl border border-[#dce9ff] bg-gradient-to-br from-[#eaf2ff] via-white to-white px-6 py-7 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-2 text-xs font-semibold tracking-[0.14em] text-[#1e6fff]">TASK MARKET</div>
          <h1 className="m-0 text-3xl font-bold tracking-tight text-[#172033]">任务大厅</h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-text-secondary">浏览公开的联邦学习需求。需求方可以发布任务，数据提供方可以查看匹配机会，原始数据始终留在本地。</p>
        </div>
        {hasPermission('task:publish') && <Button className="shrink-0" onClick={() => navigate('/app/tasks/publish')}>发布任务</Button>}
      </header>

      <section className="grid gap-3 md:grid-cols-2">
        <button type="button" onClick={() => navigate(hasPermission('task:publish') ? '/app/tasks/publish' : '/app/my-tasks')} className="group rounded-2xl border border-[#e7edf5] bg-white p-5 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-[#c7dcff] hover:shadow-[0_12px_26px_rgba(30,111,255,0.1)]">
          <div className="mb-2 text-sm font-semibold text-[#172033]">我有一个训练需求 <span className="text-[#1e6fff] transition-transform group-hover:translate-x-1">→</span></div>
          <p className="m-0 text-xs leading-5 text-text-secondary">发布任务、设置训练目标和奖励池，平台会协助寻找合适的数据节点。</p>
        </button>
        <button type="button" onClick={() => navigate(isProvider ? '/app/matching' : '/app/my-tasks')} className="group rounded-2xl border border-[#e7edf5] bg-white p-5 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-[#cdebdc] hover:shadow-[0_12px_26px_rgba(21,149,112,0.1)]">
          <div className="mb-2 text-sm font-semibold text-[#172033]">我有可协作的数据 <span className="text-[#159570] transition-transform group-hover:translate-x-1">→</span></div>
          <p className="m-0 text-xs leading-5 text-text-secondary">先登记数据资产，再查看推荐任务；参与训练时不需要上传原始数据。</p>
        </button>
      </section>

      {loading ? (
        <div className="rounded-2xl border border-border-light bg-white py-20 text-center text-text-secondary">正在加载任务...</div>
      ) : data.length === 0 ? (
        <div className="rounded-2xl border border-border-light bg-white py-20 text-center">
          <p className="text-lg font-semibold text-[#172033]">暂时还没有公开任务</p>
          <p className="mt-2 text-sm text-text-tertiary">如果你是需求方，可以发布第一个任务；如果你是数据方，可以先完善数据资产。</p>
          {hasPermission('task:publish') && <Button className="mt-5" onClick={() => navigate('/app/tasks/publish')}>发布第一个任务</Button>}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data.map((task, index) => (
            <Card 
              key={task.key} 
              hoverEffect 
              className="cursor-pointer border-border-light bg-white transition-all duration-200 hover:border-[#c7dcff] hover:shadow-[0_12px_26px_rgba(30,111,255,0.1)]"
              style={{ animationDelay: `${index * 100}ms` }}
              onClick={() => navigate(`/app/tasks/${task.key}`)}
            >
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start">
                  <CardTitle className="text-lg font-semibold text-[#172033]">
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
                    <Button variant="secondary" size="sm" className="hover:border-accent hover:bg-accent hover:text-white transition-all">
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
