import * as React from 'react';
import { cancelPreprojectTask, listPreprojectTasks, retryPreprojectTask } from '@/services/api/preprojectData';
import { useWorkspace } from '../layout/PreprojectLayout';

export function TasksPage() {
  const { taskId, task, chooseTask, go, refreshTask } = useWorkspace();
  const [tasks, setTasks] = React.useState<Awaited<ReturnType<typeof listPreprojectTasks>>['items']>([]); const [error, setError] = React.useState('');
  const refresh = React.useCallback(() => listPreprojectTasks().then((data) => setTasks(data.items)).catch(() => setError('任务列表加载失败')), []);
  React.useEffect(() => { void refresh(); }, [refresh]);
  const cancel = async () => { try { await cancelPreprojectTask(taskId); refreshTask(); } catch { setError('取消失败，任务可能已经结束。'); } };
  const retry = async () => { try { const response = await retryPreprojectTask(taskId); chooseTask(response.task.task_id, response.task.source_id); } catch { setError('重试失败，请检查任务状态。'); } };
  const stages = task?.statistics?.stages as Array<{stage: string; status: string; input_count: number; output_count: number; processed_count: number; error_count: number; duration_seconds: number; rules: unknown}> | undefined;
  const statusLabel: Record<string,string> = {pending:'等待中',running:'治理中',completed:'已完成',failed:'失败',cancelled:'已取消'};
  return <section className="rounded-xl border bg-white p-5 space-y-4"><div className="flex justify-between"><h2 className="text-lg font-semibold">任务监控</h2><button onClick={() => { void refresh(); refreshTask(); }}>刷新</button></div>{error && <p role="alert">{error}</p>}
    <div className="grid gap-2 md:grid-cols-2">{tasks.map((item) => <button key={item.task_id} onClick={() => chooseTask(item.task_id, item.source_id)} className={`rounded border p-3 text-left ${item.task_id === taskId ? 'border-blue-600 bg-blue-50' : ''}`}>{statusLabel[item.status] || item.status} · {item.current_step}<div className="truncate text-xs">{item.task_id}</div><div>{item.processed} / {item.total} 条</div></button>)}</div>
    {!tasks.length && <p>暂无任务，请先配置并启动。</p>}{taskId && !task && <p>任务状态加载中；如持续失败，请点击刷新。</p>}
    {task && <><div className="flex flex-wrap gap-3"><b>{statusLabel[task.status] || task.status} · {task.current_step}</b><span>{task.processed} / {task.total} 条</span>{['pending','running'].includes(task.status) && <button onClick={cancel}>取消任务</button>}{task.status === 'failed' && <button onClick={retry}>失败重试</button>}{task.status === 'completed' && <button onClick={() => go('quality')} className="rounded bg-blue-700 px-3 py-1 text-white">查看质量报告</button>}</div>{task.error && <p role="alert">{task.error}</p>}
      <ol aria-label="任务阶段时间线" className="grid gap-2 md:grid-cols-5">{[['schema_and_cleaning','读取与清洗'],['deduplication','去重'],['privacy','脱敏'],['quality_report','质量评价'],['completed','结果生成']].map(([key,label]) => { const seen = (task.logs || []).some((entry) => entry.stage === key); const cleanRules = stages?.find((stage) => stage.stage === 'normalize_clean')?.rules as {cleaning_enabled?: boolean} | undefined; const lastStage = task.logs?.[task.logs.length - 1]?.stage; const state = task.status === 'completed' ? key === 'schema_and_cleaning' && cleanRules?.cleaning_enabled === false ? '读取完成，清洗跳过' : '已完成' : task.status === 'failed' && lastStage === key ? '失败' : task.current_step === key ? '执行中' : seen ? '已进入' : '等待中'; return <li key={key} className="rounded bg-gray-50 p-2 text-sm">{label}<b className="block">{state}</b></li>; })}</ol>
      <h3 className="font-semibold">执行阶段</h3>{stages?.length ? stages.map((stage) => <details key={stage.stage} className="rounded border p-3"><summary>{stage.stage} · {stage.status} · {stage.input_count} → {stage.output_count} 条</summary><p>处理 {stage.processed_count} · 异常 {stage.error_count} · {stage.duration_seconds} 秒</p><pre className="whitespace-pre-wrap text-xs">{JSON.stringify(stage.rules, null, 2)}</pre><button onClick={() => go('quality', { issue: `stage:${stage.stage}` })}>查看该阶段异常样本</button></details>) : <p>阶段运行记录将在处理完成后展示；当前步骤：{task.current_step}。</p>}
      <details><summary>任务日志</summary>{(task.logs || []).map((entry, index) => <p key={index} className="text-xs">{entry.time} · {entry.stage} · {entry.processed ?? '—'} / {entry.total ?? '—'}</p>)}</details></>}
  </section>;
}
