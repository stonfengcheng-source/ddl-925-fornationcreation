import * as React from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { getPreprojectTask, listPreprojectSources, type PreprojectSource, type PreprojectTask } from '@/services/api/preprojectData';
import { useResource } from '../hooks/useResource';

interface Workspace {
  sourceId: string; taskId: string; sources: PreprojectSource[]; task: PreprojectTask | null;
  chooseSource: (id: string) => void; chooseTask: (id: string, sourceId: string) => void;
  go: (section: string, params?: Record<string, string>) => void; refreshSources: () => void;
  refreshTask: () => void;
}
const Context = React.createContext<Workspace | null>(null);
export function useWorkspace(): Workspace { const value = React.useContext(Context); if (!value) throw new Error('工作台上下文不可用'); return value; }
export const sectionNames: Record<string, string> = { sources: '数据源', pipelines: '处理配置', tasks: '任务监控', quality: '质量分析', reviews: '人工复核', versions: '版本与交付' };

export function PreprojectLayout({ children }: { children: React.ReactNode }) {
  const { section = 'sources' } = useParams(); const navigate = useNavigate();
  const [params, setParams] = useSearchParams(); const sourceId = params.get('source_id') || ''; const taskId = params.get('task_id') || '';
  const sourceLoader = React.useCallback((signal: AbortSignal) => listPreprojectSources(signal), []);
  const sources = useResource('sources', true, sourceLoader);
  React.useEffect(() => {
    if (sourceId || taskId || section !== 'sources') return;
    const example = sources.data?.items.find(item => item.is_platform_default && item.default_ready);
    if (example) setParams(current => { const next = new URLSearchParams(current); next.set('source_id', example.source_id); return next; }, {replace:true});
  }, [sourceId, taskId, section, sources.data, setParams]);
  const [task, setTask] = React.useState<PreprojectTask | null>(null);
  const [taskError, setTaskError] = React.useState(false);
  const [taskRefresh, setTaskRefresh] = React.useState(0);
  React.useEffect(() => {
    setTask(null); setTaskError(false); if (!taskId) return undefined;
    const controller = new AbortController(); let timer: number | undefined; let failures = 0;
    const poll = async () => {
      try { const next = await getPreprojectTask(taskId, controller.signal); if (controller.signal.aborted) return; setTask(next); failures = 0;
        if (sourceId !== next.source_id) setParams(current => { const updated = new URLSearchParams(current); updated.set('source_id', next.source_id); ['issue','left_version','right_version'].forEach(key => updated.delete(key)); return updated; }, {replace:true});
        if (next.status === 'running' || next.status === 'pending') timer = window.setTimeout(poll, 2000);
      } catch { if (!controller.signal.aborted) { if (failures++ < 3) timer = window.setTimeout(poll, 500 * (2 ** failures)); else setTaskError(true); } }
    };
    void poll(); return () => { controller.abort(); window.clearTimeout(timer); };
  }, [taskId, taskRefresh, sourceId, setParams]);
  const clearSelection = (query: URLSearchParams) => { ['issue', 'left_version', 'right_version'].forEach((key) => query.delete(key)); };
  const go = (next: string, updates: Record<string, string> = {}) => { const query = new URLSearchParams(params); if (updates.task_id && updates.task_id !== query.get('task_id')) clearSelection(query); Object.entries(updates).forEach(([key, value]) => value ? query.set(key, value) : query.delete(key)); navigate(`/app/data-governance/${next}${query.size ? `?${query}` : ''}`); };
  const chooseSource = (id: string) => setParams((current) => { const next = new URLSearchParams(current); if (current.get('source_id') !== id) { next.delete('task_id'); clearSelection(next); } id ? next.set('source_id', id) : next.delete('source_id'); return next; }, { replace: true });
  const chooseTask = (id: string, source: string) => setParams((current) => { const next = new URLSearchParams(current); if (current.get('task_id') !== id) clearSelection(next); next.set('source_id', source); next.set('task_id', id); return next; }, { replace: true });
  const selected = sources.data?.items.find((item) => item.source_id === sourceId);
  const matchingTask = task?.task_id === taskId && task.source_id === sourceId ? task : null;
  const taskLabel: Record<PreprojectTask['status'], string> = {pending:'等待中', running:'治理中', completed:'已完成', failed:'失败', cancelled:'已取消'};
  return <Context.Provider value={{ sourceId, taskId, sources: sources.data?.items || [], task: matchingTask, chooseSource, chooseTask, go, refreshSources: sources.refresh, refreshTask: () => setTaskRefresh((v) => v + 1) }}>
    <main className="mx-auto max-w-7xl space-y-5 p-6 text-text">
      <header><h1 className="text-2xl font-semibold">数据治理与质量评价</h1><p className="mt-1 text-sm text-text-secondary">通过标准化清洗、去重、脱敏与五维质量评价，构建可追溯的数据集。</p></header>
      <div className="rounded-lg border bg-white p-3 text-sm">当前数据：{selected?.dataset_id || (taskId ? '正在读取' : '未选择')} · {selected?.source_type === 'test_fixture' ? '平台合成数据' : selected ? '用户数据 / 来源待核验' : '请选择数据'} · 任务：{matchingTask ? taskLabel[matchingTask.status] : taskId ? '正在读取' : '未选择'}</div>
      {sources.error && <p role="alert">数据源加载失败。<button onClick={sources.refresh}>重试</button></p>}
      {taskError && <p role="alert">任务状态加载失败。<button onClick={() => setTaskRefresh((v) => v + 1)}>重试任务状态</button></p>}
      <nav aria-label="数据治理业务流程" className="flex flex-wrap gap-2 border-b pb-3">{Object.entries(sectionNames).map(([key, label]) => <button key={key} type="button" aria-current={section === key ? 'page' : undefined} onClick={() => go(key)} className={`rounded px-3 py-2 text-sm ${section === key ? 'bg-blue-700 text-white' : 'border bg-white'}`}>{label}</button>)}</nav>
      {children}
    </main>
  </Context.Provider>;
}
