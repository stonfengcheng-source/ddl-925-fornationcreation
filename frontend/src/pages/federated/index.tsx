import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Database,
  Info,
  LoaderCircle,
  Play,
  RefreshCw,
} from 'lucide-react';
import request from '@/services/request';

interface TaskSummary {
  id: string;
  task_name: string;
  task_description?: string;
  status: string;
  model_type?: string;
  max_rounds?: number;
  current_round?: number;
  current_accuracy?: number | null;
  participant_count?: number;
}

interface TrainingStatus {
  task_id: string;
  task_name: string;
  status: string;
  mode?: string;
  current_round: number;
  total_rounds: number;
  accuracy: number;
  loss: number;
  participants: number;
}

const unwrap = <T,>(response: any): T => (response?.data ?? response) as T;

const statusText: Record<string, string> = {
  pending: '待启动',
  matching: '匹配中',
  training: '训练中',
  running: '训练中',
  completed: '已完成',
  settled: '已结算',
  failed: '需处理',
};

const modelText: Record<string, string> = {
  breast_cancer: '乳腺癌二分类',
  diabetes_mlp: '糖尿病预测',
  heart_disease: '心脏病风险',
  credit_score: '信用评估',
  adult_income: '收入预测',
  bank_marketing: '银行营销',
};

const Stage: React.FC<{
  index: string;
  label: string;
  active?: boolean;
  complete?: boolean;
}> = ({ index, label, active, complete }) => (
  <div className="flex items-center gap-2">
    <span
      className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold ${
        complete
          ? 'bg-[#159570] text-white'
          : active
            ? 'bg-[#1e6fff] text-white'
            : 'bg-[#edf2f8] text-[#8190a5]'
      }`}
    >
      {complete ? <Check className="h-3.5 w-3.5" /> : index}
    </span>
    <span className={`text-sm ${active || complete ? 'font-semibold text-[#172033]' : 'text-text-tertiary'}`}>{label}</span>
  </div>
);

const FederatedLearning: React.FC = () => {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState('');
  const [trainingStatus, setTrainingStatus] = useState<TrainingStatus | null>(null);
  const [loadingTasks, setLoadingTasks] = useState(true);
  const [taskLoadError, setTaskLoadError] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [starting, setStarting] = useState(false);
  const [showNodeInfo, setShowNodeInfo] = useState(false);

  const selectedTask = useMemo(
    () => tasks.find((task) => task.id === selectedTaskId) || null,
    [selectedTaskId, tasks],
  );

  const loadTasks = useCallback(async () => {
    setLoadingTasks(true);
    try {
      const response = await request.get('/tasks');
      const list = unwrap<TaskSummary[]>(response);
      const nextTasks = Array.isArray(list) ? list : [];
      setTasks(nextTasks);
      setTaskLoadError(false);
      setSelectedTaskId((current) => (current && nextTasks.some((task) => task.id === current) ? current : nextTasks[0]?.id || ''));
    } catch {
      setTasks([]);
      setTaskLoadError(true);
    } finally {
      setLoadingTasks(false);
    }
  }, []);

  const loadTrainingStatus = useCallback(async () => {
    if (!selectedTaskId) {
      setTrainingStatus(null);
      return;
    }

    setLoadingStatus(true);
    try {
      const response = await request.get(`/training/${selectedTaskId}/status`);
      setTrainingStatus(unwrap<TrainingStatus>(response));
    } catch {
      setTrainingStatus(null);
    } finally {
      setLoadingStatus(false);
    }
  }, [selectedTaskId]);

  useEffect(() => {
    void loadTasks();
  }, [loadTasks]);

  useEffect(() => {
    void loadTrainingStatus();
  }, [loadTrainingStatus]);

  useEffect(() => {
    if (!selectedTaskId || !['training', 'running'].includes(trainingStatus?.status || '')) return undefined;
    const timer = window.setInterval(() => void loadTrainingStatus(), 5000);
    return () => window.clearInterval(timer);
  }, [loadTrainingStatus, selectedTaskId, trainingStatus?.status]);

  const taskStatus = trainingStatus?.status || selectedTask?.status || '';
  const isTraining = ['training', 'running'].includes(taskStatus);
  const isCompleted = ['completed', 'settled'].includes(taskStatus);
  const totalRounds = trainingStatus?.total_rounds || selectedTask?.max_rounds || 5;
  const currentRound = isCompleted ? totalRounds : trainingStatus?.current_round || selectedTask?.current_round || 0;
  const progress = isCompleted ? 100 : Math.min(100, Math.round((currentRound / Math.max(totalRounds, 1)) * 100));
  const selectedModel = selectedTask?.model_type || 'breast_cancer';
  const demoSupported = selectedModel === 'breast_cancer';

  const handleSelectTask = (taskId: string) => {
    setSelectedTaskId(taskId);
    setTrainingStatus(null);
  };

  const handleStartDemo = async () => {
    if (!selectedTaskId) return;
    setStarting(true);
    try {
      await request.post(`/training/${selectedTaskId}/start?mode=demo`);
      message.success('训练已启动');
      window.setTimeout(() => void loadTrainingStatus(), 300);
    } catch (error: any) {
      const detail = error?.response?.data?.detail || '启动失败，请先确认后端服务和联邦学习依赖已准备好';
      message.error(detail);
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="mx-auto w-full min-w-0 max-w-[1180px] space-y-5 pb-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-3 flex items-center gap-2 text-sm">
            <button
              type="button"
              onClick={() => navigate('/app/dashboard')}
              className="inline-flex items-center gap-1.5 text-text-secondary transition-colors hover:text-[#1e6fff]"
            >
              <ArrowLeft className="h-4 w-4" />
              返回工作台
            </button>
          </div>
          <h1 className="m-0 text-3xl font-bold tracking-tight text-[#172033]">联邦学习</h1>
          <p className="mt-2 text-sm text-text-secondary">选择任务，启动一次本机演示训练。</p>
        </div>
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <span className="inline-flex items-center gap-2 rounded-full bg-[#eef8f4] px-3 py-2 text-xs font-semibold text-[#159570]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#159570]" />
            本机演示
          </span>
          <button
            type="button"
            onClick={() => void loadTasks()}
            className="rounded-lg border border-border-light bg-white p-2.5 text-text-secondary transition-colors hover:border-[#c8dafa] hover:text-[#1e6fff]"
            aria-label="刷新任务"
            title="刷新任务"
          >
            <RefreshCw className={`h-4 w-4 ${loadingTasks ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </header>

      <section className="overflow-hidden rounded-[26px] border border-[#dce9ff] bg-white shadow-[0_12px_34px_rgba(30,111,255,0.06)]">
        <div className="flex flex-col gap-7 bg-gradient-to-r from-[#edf5ff] via-[#f8fbff] to-white px-6 py-6 sm:px-8 sm:py-7 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="text-xs font-semibold tracking-[0.13em] text-[#1e6fff]">训练工作区</div>
            <h2 className="m-0 mt-2 text-2xl font-bold tracking-tight text-[#172033]">从一个任务开始</h2>
            <p className="mt-2 text-sm text-text-secondary">内置样例数据会在本机启动两个模拟节点，适合先验证完整链路。</p>
          </div>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-3 lg:min-w-[410px] lg:justify-end">
            <Stage index="1" label="选择任务" active={!selectedTaskId} complete={Boolean(selectedTaskId)} />
            <span className="hidden h-px w-8 bg-[#d8e4f5] sm:block" />
            <Stage index="2" label="训练中" active={isTraining} complete={isCompleted} />
            <span className="hidden h-px w-8 bg-[#d8e4f5] sm:block" />
            <Stage index="3" label="查看结果" active={isCompleted} complete={isCompleted} />
          </div>
        </div>
        <div className="flex flex-col gap-2 border-t border-[#eaf0f7] px-6 py-3.5 text-xs text-text-secondary sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span className="inline-flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-[#159570]" />
            原始数据保留在本地，仅交换训练参数
          </span>
          <button type="button" onClick={() => setShowNodeInfo((value) => !value)} className="text-left font-medium text-[#1e6fff] hover:text-[#1557c0] sm:text-right">
            {showNodeInfo ? '收起节点接入说明' : '节点接入说明'}
          </button>
        </div>
        {showNodeInfo && (
          <div className="border-t border-[#eaf0f7] bg-[#fbfdff] px-6 py-3.5 text-xs leading-5 text-text-secondary sm:px-8">
            真实节点模式需要安装节点客户端并完成网络配置；当前先提供本机演示入口，后续可在此处切换。
          </div>
        )}
      </section>

      <section className="grid min-w-0 gap-5 lg:grid-cols-[0.92fr_1.08fr]">
        <section className="min-w-0 overflow-hidden rounded-[24px] border border-border-light bg-white shadow-[0_8px_24px_rgba(23,32,51,0.035)]">
          <div className="flex items-center justify-between border-b border-[#eaf0f7] px-6 py-5">
            <div>
              <h2 className="m-0 text-lg font-bold text-[#172033]">训练任务</h2>
              <p className="mt-1 text-xs text-text-tertiary">选择要运行的任务</p>
            </div>
            <span className="text-xs text-text-tertiary">{loadingTasks ? '读取中' : `${tasks.length} 个任务`}</span>
          </div>

          {loadingTasks ? (
            <div className="flex min-h-56 items-center justify-center text-sm text-text-tertiary">
              <LoaderCircle className="mr-2 h-5 w-5 animate-spin" />
              正在读取任务
            </div>
          ) : tasks.length ? (
            <div className="divide-y divide-[#edf1f6]">
              {tasks.map((task) => {
                const selected = task.id === selectedTaskId;
                const taskModel = task.model_type || 'breast_cancer';
                return (
                  <button
                    key={task.id}
                    type="button"
                    onClick={() => handleSelectTask(task.id)}
                    aria-pressed={selected}
                    className={`relative flex w-full items-center gap-3 px-6 py-4 text-left transition-colors ${selected ? 'bg-[#f4f8ff]' : 'hover:bg-[#fbfdff]'}`}
                  >
                    <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${selected ? 'bg-[#1e6fff] text-white' : 'bg-[#edf3fb] text-[#6c7c93]'}`}>
                      <Database className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <span className="truncate text-sm font-semibold text-[#172033]">{task.task_name}</span>
                        <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] ${selected ? 'bg-white text-[#1e6fff]' : 'bg-[#f3f5f8] text-text-secondary'}`}>
                          {statusText[task.status] || task.status}
                        </span>
                      </span>
                      <span className="mt-1 block truncate text-xs text-text-tertiary">{modelText[taskModel] || taskModel}</span>
                    </span>
                    {selected && <Check className="h-5 w-5 shrink-0 text-[#1e6fff]" />}
                  </button>
                );
              })}
            </div>
          ) : taskLoadError ? (
            <div className="px-6 py-12 text-center">
              <Info className="mx-auto h-7 w-7 text-[#e88918]" />
              <div className="mt-3 text-sm font-semibold text-[#172033]">后端暂时不可用</div>
              <p className="mt-1 text-xs text-text-tertiary">启动后端服务后重新刷新。</p>
              <button type="button" onClick={() => void loadTasks()} className="mt-4 inline-flex items-center gap-2 rounded-lg border border-[#f1c77e] px-3.5 py-2 text-sm font-semibold text-[#a66a11] hover:bg-[#fffaf0]">
                重新连接 <RefreshCw className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div className="px-6 py-12 text-center">
              <Database className="mx-auto h-7 w-7 text-[#a6b3c5]" />
              <div className="mt-3 text-sm font-semibold text-[#172033]">暂无可训练任务</div>
              <p className="mt-1 text-xs text-text-tertiary">先发布任务，再回到这里开始训练。</p>
              <button type="button" onClick={() => navigate('/app/tasks/publish')} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-[#1e6fff] px-3.5 py-2 text-sm font-semibold text-white hover:bg-[#1557c0]">
                发布任务 <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </section>

        <section className="min-w-0 rounded-[24px] border border-[#dce9ff] bg-[#fbfdff] p-6 shadow-[0_8px_24px_rgba(30,111,255,0.045)] sm:p-7">
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs font-semibold tracking-[0.13em] text-[#1e6fff]">当前操作</div>
            {loadingStatus && selectedTaskId && <LoaderCircle className="h-4 w-4 animate-spin text-[#1e6fff]" />}
          </div>

          {selectedTask ? (
            <div className="mt-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h2 className="m-0 truncate text-2xl font-bold tracking-tight text-[#172033]">{selectedTask.task_name}</h2>
                  <p className="mt-2 truncate text-sm text-text-secondary">{selectedTask.task_description || modelText[selectedModel] || selectedModel}</p>
                </div>
                <span className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold ${isTraining ? 'bg-[#eef5ff] text-[#1e6fff]' : isCompleted ? 'bg-[#eef8f4] text-[#159570]' : 'bg-[#f3f5f8] text-text-secondary'}`}>
                  {isTraining ? '训练中' : isCompleted ? '已完成' : '待启动'}
                </span>
              </div>

              <div className="mt-5 flex flex-wrap gap-2">
                <span className="rounded-full bg-[#eef5ff] px-3 py-1.5 text-xs font-medium text-[#1e6fff]">{modelText[selectedModel] || selectedModel}</span>
                <span className="rounded-full bg-white px-3 py-1.5 text-xs font-medium text-text-secondary ring-1 ring-[#e4ebf4]">{totalRounds} 轮训练</span>
                <span className="rounded-full bg-white px-3 py-1.5 text-xs font-medium text-text-secondary ring-1 ring-[#e4ebf4]">2 个模拟节点</span>
              </div>

              <div className="my-6 border-t border-[#e7eef8]" />

              {!demoSupported && (
                <div className="mb-4 flex gap-2 rounded-xl bg-[#fff7e8] px-3 py-2.5 text-xs leading-5 text-[#a66a11]">
                  <Info className="mt-0.5 h-4 w-4 shrink-0" />
                  当前本机演示仅支持乳腺癌示例模型。
                </div>
              )}

              <button
                type="button"
                disabled={starting || isTraining || !demoSupported}
                onClick={() => void handleStartDemo()}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#1e6fff] px-4 py-3.5 text-sm font-semibold text-white shadow-[0_8px_18px_rgba(30,111,255,0.18)] transition-all hover:-translate-y-0.5 hover:bg-[#1557c0] disabled:cursor-not-allowed disabled:bg-[#a9c8ff] disabled:shadow-none"
              >
                {starting ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                {isTraining ? '训练正在进行' : starting ? '正在启动' : isCompleted ? '重新运行演示' : '开始训练'}
              </button>
              <p className="mt-3 text-center text-xs text-text-tertiary">本机演示不需要配置节点或端口。</p>

              {(isTraining || isCompleted) && (
                <div className="mt-6 border-t border-[#e7eef8] pt-5">
                  <div className="flex items-center justify-between text-xs text-text-secondary">
                    <span>{isCompleted ? '训练已完成' : '训练进行中'}</span>
                    <span className="font-semibold text-[#1e6fff]">{progress}%</span>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-[#e8eef7]">
                    <div className="h-full rounded-full bg-gradient-to-r from-[#1e6fff] to-[#63a7ff] transition-all" style={{ width: `${progress}%` }} />
                  </div>
                  <div className="mt-4 flex items-end justify-between">
                    <div>
                      <div className="text-2xl font-bold text-[#172033]">{currentRound}<span className="ml-1 text-sm font-medium text-text-tertiary">/ {totalRounds} 轮</span></div>
                      <div className="mt-1 text-xs text-text-tertiary">训练进度</div>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-[#159570]">{trainingStatus?.accuracy ? `${(trainingStatus.accuracy * 100).toFixed(1)}%` : '-'}</div>
                      <div className="mt-1 text-xs text-text-tertiary">当前准确率</div>
                    </div>
                  </div>
                  <button type="button" onClick={() => navigate(`/app/federated/training/${selectedTaskId}`)} className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl border border-[#cfe0fb] px-4 py-2.5 text-sm font-semibold text-[#1e6fff] transition-colors hover:bg-[#f1f6ff]">
                    查看训练监控 <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex min-h-64 flex-col items-center justify-center text-center">
              <Database className="h-8 w-8 text-[#a6b3c5]" />
              <div className="mt-3 text-sm font-semibold text-[#172033]">先选择一个任务</div>
              <p className="mt-1 text-xs text-text-tertiary">训练设置会显示在这里。</p>
            </div>
          )}
        </section>
      </section>

      <footer className="flex flex-col gap-3 border-t border-[#e5ebf3] pt-4 text-xs text-text-tertiary sm:flex-row sm:items-center sm:justify-between">
        <span>训练结果可在监控页查看，任务本身不会被修改。</span>
        <button type="button" onClick={() => navigate('/app/tasks')} className="inline-flex items-center gap-1.5 font-medium text-[#1e6fff] hover:text-[#1557c0]">
          查看任务大厅 <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </footer>
    </div>
  );
};

export default FederatedLearning;
