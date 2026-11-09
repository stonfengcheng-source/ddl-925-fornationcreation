import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert, Button, Card, Checkbox, Col, Form, Input, InputNumber, Row, Select, Space, Table, Tabs, Tag, Typography, message,
} from 'antd';
import {
  clearModule4Logs, getModule4Results, getModule4Status, runModule4, stopModule4, getCandidateVersions, prepareCandidateConfig, getModule4Preflight,
} from '@/services/api/module4';
import type { CandidateVersion, Module4Action, Module4Config, Module4Preflight, Module4Status, ResultRow } from '@/services/api/module4';
import { evaluationModeOptions, evaluationPreset, evaluationSubjects } from '@/config/module4Evaluation';
import request from '@/services/request';

const defaults: Module4Config = {
  training_python: '',
  predictions_path: '',
  badcase_model: 'ours',
  raw_path: 'demo-datasets/education-synthetic/raw_5k.jsonl',
  evaluated_path: '',
  datajuicer_path: '',
  sample_count: 100,
  seed: 42,
  base_model: 'Qwen/Qwen2.5-0.5B-Instruct',
  template: 'qwen',
  epochs: 1,
  precision: 'bf16',
  variant: 'all',
  opencompass_env: 'D:\\opencompass_env',
  eval_workspace: 'experiments/module4/opencompass-workspace',
  eval_mode: 'quick',
  ...evaluationPreset('quick')!,
  eval_batch_size: 1,
  eval_max_out_len: 512,
  eval_model: 'all',
  data_version_id: '', candidate_config_id: '',
};
const storageKey = 'module4.platform.config';
const variants = [
  { value: 'all', label: '全部可用组' },
  { value: 'raw', label: 'Raw' },
  { value: 'rule', label: 'Rule' },
  { value: 'llm_only', label: 'LLM-only' },
  { value: 'datajuicer', label: 'Data-Juicer' },
  { value: 'ours', label: 'Ours' },
];
const statuses = {
  idle: '等待任务', running: '运行中', stopping: '正在停止',
  success: '已完成', failed: '执行失败', stopped: '已停止',
};
const artifactNames: Record<string, string> = {
  environment_report: '环境检查', datasets: '训练数据', validation: '数据校验',
  configs: '训练配置', checkpoints: '微调模型', merged: '合并模型',
  eval_manifest: '评测配置', summary: '结果汇总',
};
const required = [{ required: true, message: '请填写此项' }];
const resultProjectKey = (row: ResultRow) => JSON.stringify([row.benchmark, row.metric]);
const projectNames: Record<string, string> = {
  overall_macro: '总体平均', ceval_macro: 'C-Eval 平均', cmmlu_macro: 'CMMLU 平均',
};

function initialConfig(): Module4Config {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
    const isRetiredInput = (value: unknown, filename: string) => {
      if (typeof value !== 'string') return false;
      const path = value.trim().replace(/\\/g, '/').toLowerCase();
      return path === `test_data/${filename}` || path.endsWith(`/test_data/${filename}`);
    };
    const hadRetiredInput = isRetiredInput(saved?.raw_path, 'raw_test.jsonl')
      || isRetiredInput(saved?.evaluated_path, 'quality_eval_test.jsonl')
      || isRetiredInput(saved?.datajuicer_path, 'datajuicer_test.jsonl');
    if (isRetiredInput(saved?.raw_path, 'raw_test.jsonl')) {
      saved.raw_path = defaults.raw_path;
    }
    for (const [field, filename] of [['evaluated_path', 'quality_eval_test.jsonl'], ['datajuicer_path', 'datajuicer_test.jsonl']]) {
      if (isRetiredInput(saved?.[field], filename)) saved[field] = '';
    }
    if (hadRetiredInput && saved.sample_count === 4) saved.sample_count = defaults.sample_count;
    const config = Object.fromEntries(Object.entries(defaults).map(([key, value]) => [
      key, (Array.isArray(value) ? Array.isArray(saved?.[key]) : typeof saved?.[key] === typeof value) ? saved[key] : value,
    ])) as unknown as Module4Config;
    if (!evaluationModeOptions.some(option => option.value === config.eval_mode)) config.eval_mode = 'quick';
    const preset = evaluationPreset(config.eval_mode);
    if (preset) Object.assign(config, preset);
    else config.eval_subjects = config.eval_subjects.filter(value => evaluationSubjects.some(subject => subject.value === value));
    return config;
  } catch {
    return defaults;
  }
}

function apiErrorMessage(error: any): string {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (detail && typeof detail === 'object') return [detail.message, ...(Array.isArray(detail.reasons) ? detail.reasons : [])].filter(Boolean).join('；');
  return error?.message || '任务未能启动，请检查参数和运行环境。';
}

export default function Module4() {
  const [form] = Form.useForm<Module4Config>();
  const [config, setConfig] = useState(initialConfig);
  const [status, setStatus] = useState<Module4Status | null>(null);
  const [connectionError, setConnectionError] = useState('');
  const [requestError, setRequestError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [revision, setRevision] = useState(0);
  const [rows, setRows] = useState<ResultRow[]>([]);
  const [candidateVersions, setCandidateVersions] = useState<CandidateVersion[]>([]);
  const [modelResources, setModelResources] = useState<Array<{id?: string; name: string; ready: boolean}>>([]);
  useEffect(() => { let active = true; request.get('/preproject-data/resources').then((value) => { if (active) setModelResources((value as unknown as {models: Array<{id?: string; name: string; ready: boolean}>}).models || []); }).catch(() => undefined); return () => { active = false; }; }, []);
  const [preflight, setPreflight] = useState<Module4Preflight | null>(null);
  const [preflightError, setPreflightError] = useState('');
  const [preflightRevision, setPreflightRevision] = useState(0);
  const [selectedProject, setSelectedProject] = useState('');
  const resultProjects = useMemo(() => {
    const models = new Set(rows.map(row => row.model));
    const projects = new Map<string, { benchmark: string; metric: string; models: Set<string> }>();
    for (const row of rows) {
      const key = resultProjectKey(row);
      const project = projects.get(key) ?? { benchmark: row.benchmark, metric: row.metric, models: new Set<string>() };
      project.models.add(row.model);
      projects.set(key, project);
    }
    const priority = (benchmark: string) => ['overall_macro', 'ceval_macro', 'cmmlu_macro'].indexOf(benchmark);
    return [...projects.entries()].map(([value, project]) => {
      const complete = project.models.size === models.size;
      const name = projectNames[project.benchmark] ? `${project.benchmark}（${projectNames[project.benchmark]}）` : project.benchmark;
      return { value, benchmark: project.benchmark, label: `${name} · ${project.metric}${complete ? '' : '（结果未齐）'}`, disabled: !complete };
    }).sort((a, b) => {
      const rankA = priority(a.benchmark), rankB = priority(b.benchmark);
      return (rankA < 0 ? 3 : rankA) - (rankB < 0 ? 3 : rankB) || a.label.localeCompare(b.label);
    });
  }, [rows]);
  const comparisonProject = resultProjects.find(project => project.value === selectedProject && !project.disabled)
    ?? resultProjects.find(project => !project.disabled);
  const comparisonRows = rows.filter(row => resultProjectKey(row) === comparisonProject?.value);
  const logRef = useRef<HTMLPreElement>(null);
  const busy = status?.task.status === 'running' || status?.task.status === 'stopping';
  const disabled = !status || busy || submitting || Boolean(connectionError);
  const available = status?.available_variants ?? ['raw'];
  const pending = status?.pending_variants ?? {
    ...(!config.evaluated_path.trim() ? { rule: '待接入', llm_only: '待接入', ours: '待接入' } : {}),
    ...(!config.datajuicer_path.trim() ? { datajuicer: '待接入' } : {}),
  };
  const variantOptions = variants.map(option => ({ ...option, disabled: option.value !== 'all' && !available.includes(option.value) }));
  const evaluationOptions = variants.slice(1).map(option => ({ ...option, disabled: !(status?.available_models ?? ['base']).includes(option.value) }));
  const trainingEnvironment = preflight?.training_environment ?? status?.training_environment;
  const trainingBlocked = !preflight?.training.ready;
  const progress = Object.entries(artifactNames).map(([key, label]) => {
    const value = status?.progress?.[key];
    const available = value != null && typeof value === 'object'
      ? Object.values(value).length > 0 && Object.values(value).every(member => member === true)
      : value === true;
    const parameters = status?.progress_parameters?.[key] ?? {};
    const completed = available && Object.entries(parameters).every(([field, value]) => String(config[field as keyof Module4Config]) === String(value));
    return { key, label, completed };
  });

  useEffect(() => {
    try { localStorage.setItem(storageKey, JSON.stringify(config)); } catch { /* 浏览器可能禁用存储 */ }
  }, [config]);

  useEffect(() => {
    let active = true;
    getCandidateVersions().then(({items}) => {
      if (!active) return; setCandidateVersions(items);
      const requested = new URLSearchParams(window.location.search).get('data_version_id');
      if (requested && items.some((item) => item.version_id === requested)) {
        form.setFieldsValue({data_version_id: requested, candidate_config_id: ''});
        setConfig((current) => ({...current, data_version_id: requested, candidate_config_id: ''}));
      }
    }).catch(() => { if (active) setRequestError('合格数据版本加载失败，请检查数据处理服务。'); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setPreflight(null);
    const timer = window.setTimeout(() => { getModule4Preflight(config, controller.signal).then((result) => { if (!controller.signal.aborted) { setPreflight(result); setPreflightError(''); } }).catch(() => { if (!controller.signal.aborted) setPreflightError('前置检查失败，请确认后端连接后重试。'); }); }, 350);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [config, preflightRevision, status?.task.finished_at]);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const next = await getModule4Status(controller.signal);
        if (controller.signal.aborted) return;
        setStatus(next);
        setConnectionError('');
        timer = setTimeout(poll, 2000);
      } catch {
        if (!controller.signal.aborted) setConnectionError('无法连接任务服务，请确认平台后端已启动后重新连接。');
      }
    }
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [revision]);

  useEffect(() => {
    let active = true;
    getModule4Results().then(result => {
      if (active) {
        setRows(result.rows);
      }
    }).catch(() => {
      if (active) setRequestError('评测结果读取失败，可点击“刷新结果”重试。');
    });
    return () => { active = false; };
  }, [status?.task.finished_at]);

  useEffect(() => {
    const node = logRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [status?.task.logs]);

  async function run(action: Module4Action) {
    try {
      await form.validateFields();
      const values = { ...config, ...form.getFieldsValue(true) } as Module4Config;
      setSubmitting(true);
      setRequestError('');
      const result = await runModule4(action, action === 'fix_eval_dependencies' ? {...values, confirm_install: true} : values);
      message.success(result.message);
      setStatus(await getModule4Status());
    } catch (error) {
      if (error instanceof Error) setRequestError(apiErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  function updateConfig(changed: Partial<Module4Config>, values: Module4Config) {
    if ('data_version_id' in changed) {
      values.candidate_config_id = '';
      form.setFieldValue('candidate_config_id', '');
    }
    const preset = changed.eval_mode && evaluationPreset(changed.eval_mode);
    if (preset) {
      Object.assign(values, preset);
      form.setFieldsValue(preset);
    } else if (['eval_subjects', 'eval_samples_per_subject', 'eval_all_questions'].some(key => key in changed)) {
      values.eval_mode = 'custom';
      form.setFieldValue('eval_mode', 'custom');
    }
    setConfig(current => ({ ...current, ...values }));
  }

  function selectSubjects(benchmark?: string) {
    const subjects = benchmark
      ? [...new Set([...config.eval_subjects, ...evaluationSubjects.filter(subject => subject.benchmark === benchmark).map(subject => subject.value)])]
      : [];
    form.setFieldsValue({ eval_subjects: subjects, eval_mode: 'custom' });
    setConfig(values => ({ ...values, eval_subjects: subjects, eval_mode: 'custom' }));
  }

  async function stop() {
    setSubmitting(true);
    try {
      const result = await stopModule4();
      message.info(result.message);
      setStatus(await getModule4Status());
    } catch {
      setRequestError('停止请求未成功，请确认后端连接后重试。');
    } finally { setSubmitting(false); }
  }

  async function clear() {
    try { await clearModule4Logs(); setStatus(await getModule4Status()); }
    catch { setRequestError('日志清理失败，请重试。'); }
  }

  async function refreshResults() {
    try {
      const result = await getModule4Results();
      setRows(result.rows);
      setRequestError('');
    }
    catch { setRequestError('评测结果读取失败，请重试。'); }
  }

  async function prepareVersion() {
    try {
      await form.validateFields();
      const values = { ...config, ...form.getFieldsValue(true) } as Module4Config;
      if (!values.data_version_id) { setRequestError('请先选择合格候选版本。'); return; }
      setSubmitting(true); setRequestError('');
      const prepared = await prepareCandidateConfig(values);
      form.setFieldsValue({candidate_config_id: prepared.config_id, sample_count: prepared.sample_count});
      setConfig((current) => ({...current, candidate_config_id: prepared.config_id, sample_count: prepared.sample_count}));
      message.success(prepared.message); setPreflightRevision((value) => value + 1);
    } catch (error) { if (error instanceof Error) setRequestError(apiErrorMessage(error)); }
    finally { setSubmitting(false); }
  }

  const actionButton = (label: string, action: Module4Action, primary = false) => (
    <Button type={primary ? 'primary' : 'default'}
      disabled={disabled || (['train', 'merge'].includes(action) && trainingBlocked) || (['eval_dry','eval_run','eval_score'].includes(action) && (!preflight?.evaluation.ready || (action === 'eval_run' && !preflight.evaluation.dry_run_ready) || (action === 'eval_score' && !preflight.evaluation.score_ready)))}
      title={['train', 'merge'].includes(action) && trainingBlocked ? '请先完成训练前置检查。' : ['eval_dry','eval_run','eval_score'].includes(action) && !preflight?.evaluation.ready ? '请先完成评测前置检查。' : undefined}
      onClick={() => { if (action !== 'fix_eval_dependencies' || window.confirm('将尝试在独立评测环境中安装依赖，可能需要联网。确认继续？')) void run(action); }}>{label}</Button>
  );

  return (
    <div className="space-y-6">
      <div>
        <Typography.Title level={2} style={{ marginBottom: 8 }}>训练实验与效果验证</Typography.Title>
        <Typography.Paragraph type="secondary">
          选择合格数据版本、基础模型和评测方案；资源就绪后再执行训练与评测。
        </Typography.Paragraph>
      </div>
      {connectionError && <Alert type="error" title={connectionError} action={<Button onClick={() => setRevision(value => value + 1)}>重新连接</Button>} />}
      {requestError && <Alert type="error" title={requestError} closable onClose={() => setRequestError('')} />}
      {preflightError && <Alert type="warning" message={preflightError} action={<Button onClick={() => setPreflightRevision(value => value + 1)}>重试检查</Button>} />}
      <Card title="实验概览" extra={<a href="/app/resources">准备训练环境</a>}>
        <Space wrap size="large"><Typography.Text>可选数据版本：{candidateVersions.length}</Typography.Text><Typography.Text>已登记模型：{modelResources.filter(item => item.id && item.ready).length}</Typography.Text><Typography.Text>评测资源：{preflight?.evaluation.ready ? '已就绪' : '待配置'}</Typography.Text></Space>
        <Typography.Paragraph type="secondary" style={{marginTop:12, marginBottom:0}}>{trainingEnvironment?.training_ready ? '训练资源已检查；仍需确认数据及授权。' : '当前尚未配置模型训练资源。数据治理功能不受影响。'} 生成配置后，训练仍未执行。</Typography.Paragraph>
      </Card>

      <Form form={form} layout="vertical" initialValues={config} onValuesChange={updateConfig} disabled={busy || submitting}>
        <Row gutter={[20, 20]}>
          <Col xs={24} xl={15}>
            <details><summary>查看技术详情与任务状态</summary><Card title="任务状态" extra={<Tag color={busy ? 'processing' : status?.task.status === 'failed' ? 'error' : 'default'}>{status ? statuses[status.task.status] : '连接中'}</Tag>}>
              <Typography.Paragraph>{status?.task.label || '正在连接任务服务…'}</Typography.Paragraph>
              <Typography.Paragraph type="secondary">任务由平台后端持续执行，离开页面后可以返回查看。</Typography.Paragraph>
              <Space wrap style={{ marginBottom: 16 }}>
                <Button danger disabled={!busy || submitting || status?.task.status === 'stopping'} onClick={() => void stop()}>停止当前任务</Button>
                <Button disabled={!status || busy} onClick={() => void clear()}>清空日志</Button>
              </Space>
              <pre ref={logRef} aria-label="任务日志" aria-live="off" style={{ height: 220, overflow: 'auto', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', background: '#191f2b', color: '#d6e0ef', padding: 16, borderRadius: 8, fontSize: 12, margin: 0 }}>{status?.task.logs || '任务开始后，运行日志将显示在这里。'}</pre>
              {status?.task.exit_code != null && <Typography.Text type="secondary">退出码：{status.task.exit_code}</Typography.Text>}
              {status?.task.status === 'failed' && !status.task.logs && <Alert style={{ marginTop: 12 }} type="error" showIcon
                message={`任务失败（退出码 ${status.task.exit_code ?? '未知'}）`}
                description={status.task.label === '检查训练环境' ? trainingEnvironment?.message : '后端没有返回任务日志摘要，请重新执行并保留日志后查看失败原因。'} />}
            </Card></details>
          </Col>
          <Col xs={24} xl={9}>
            <Card title="实验进度">
              <Space wrap>
                {progress.map(({ key, label, completed }) => (
                  <Tag key={key} color={completed ? 'success' : 'default'} title={completed ? '本次任务已成功完成，产物已就绪' : '本次任务尚未完成'}>{label}{completed ? ' ✓' : ''}</Tag>
                ))}
              </Space>
            </Card>
          </Col>
          <Col span={24}>
            <Tabs defaultActiveKey="data" items={[
              { key: 'data', label: '选择训练数据', children: <Space orientation="vertical" size="large" style={{ width: '100%' }}>
                <Card title="1 · 选择训练数据">
                  <Typography.Paragraph>优先使用数据治理模块的合格候选版本；版本数据仅用于本次本地配置，不自动获得发布或商业训练授权。</Typography.Paragraph>
                  <Form.Item name="data_version_id" label="合格候选数据版本"><Select allowClear placeholder="选择当前用户的数据版本" options={candidateVersions.map(item => ({value:item.version_id, label:`${item.dataset_id || '数据集'} · ${item.sample_count} 条 · ${item.release_eligible ? '可发布' : '来源许可待核验'}`}))} /></Form.Item>
                  <Form.Item name="candidate_config_id" hidden><Input /></Form.Item>
                  {!candidateVersions.length && <Alert type="info" showIcon message="还没有可用的合格版本" description={<span>请先到 <a href="/app/data-governance/sources">数据治理与质量评价</a> 导入、验证并完成处理。</span>} />}
                  {config.data_version_id && <Alert type="warning" showIcon message="已选择合格候选版本" description="可生成本地训练配置；来源版本及许可未完成核验时，不表示正式发布或商业使用已获授权。" />}
                  <details><summary>高级数据路径</summary><Typography.Paragraph type="secondary">输入文件由后端电脑读取。当前默认文件是合成演示数据，不能用于真实数据验收；请在正式实验前替换为来源明确的文件。</Typography.Paragraph>
                  <Form.Item name="raw_path" label="原始候选数据（默认：合成演示样本）" rules={config.data_version_id ? [] : required}><Input disabled={Boolean(config.data_version_id)} /></Form.Item>
                  <Form.Item name="evaluated_path" label="质量评价结果"><Input placeholder="可选；留空时跳过 Rule、LLM-only、Ours" /></Form.Item>
                  <Form.Item name="datajuicer_path" label="Data-Juicer 独立处理结果"><Input placeholder="可选；留空时跳过 Data-Juicer" /></Form.Item>
                  <Space wrap style={{ marginBottom: 16 }}>
                    {variants.filter(option => option.value in pending).map(option => <Tag key={option.value}>{option.label}：待接入</Tag>)}
                  </Space>
                  <Row gutter={16}>
                    <Col span={12}><Form.Item name="sample_count" label="每组样本数" rules={required}><InputNumber min={1} max={1000000} precision={0} style={{ width: '100%' }} /></Form.Item></Col>
                    <Col span={12}><Form.Item name="seed" label="随机种子" rules={required}><InputNumber min={0} max={2147483647} precision={0} style={{ width: '100%' }} /></Form.Item></Col>
                  </Row>
                  <Space wrap>{!config.data_version_id && actionButton('生成验证数据', 'build_data', true)}{!config.data_version_id && actionButton('校验数据', 'validate_data')}</Space></details>
                </Card>
                <details><summary>高级设置：训练和评测环境</summary><Card title="运行环境">
                  <Typography.Paragraph type="secondary">环境检查和依赖诊断在后端所选 Python 中执行。评测依赖修复只作用于配置的 OpenCompass 环境。</Typography.Paragraph>
                  {trainingEnvironment && <Alert showIcon style={{ marginBottom: 16 }} type={trainingEnvironment.training_ready ? 'success' : 'warning'}
                    message={trainingEnvironment.message || '训练环境状态已读取'}
                    description={<div>
                      <div>Python {trainingEnvironment.python_version || '未知'} · CUDA {trainingEnvironment.cuda_state === 'not_checked_without_torch' ? '未检测（缺少或无法加载 PyTorch）' : trainingEnvironment.cuda_state === 'cpu_only_pytorch' ? 'PyTorch 为 CPU 版本' : trainingEnvironment.cuda_available ? '可用' : '驱动或运行时不可用'}</div>
                      {trainingEnvironment.gpus?.length ? <div>显卡：{trainingEnvironment.gpus.join('；')}</div> : null}
                      {trainingEnvironment.missing_packages?.length ? <div>缺少：{trainingEnvironment.missing_packages.join('、')}</div> : null}
                      <div>请使用独立训练环境安装缺少的依赖；安装 CUDA 版 PyTorch 后重新检查，避免修改平台后端环境。</div>
                    </div>} />}
                  <Form.Item name="training_python" label="训练 Python（可选）" extra="高级设置：留空使用平台配置；独立环境由资源管理维护。"><Input placeholder="独立训练环境解释器（可选）" /></Form.Item>
                  <Form.Item name="opencompass_env" label="OpenCompass 评测环境" rules={required}><Input /></Form.Item>
                  <Space wrap>
                    {actionButton('检查训练环境', 'check_training_env')}
                    {actionButton('修复评测依赖', 'fix_eval_dependencies')}
                    {actionButton('检查评测环境', 'check_eval_env')}
                  </Space>
                </Card></details>
              </Space> },
              { key: 'training', label: '训练实验', children: <Card title="2 · 模型与训练配置">
                {trainingBlocked && <Alert style={{ marginBottom: 16 }} type="warning" showIcon message="尚未满足训练条件" description={<div>{(preflight?.training.checks || []).filter(item => !item.ready).map(item => <div key={item.key}>• {item.message}</div>)}<div>先完成数据、模型和独立训练环境准备，再重新检查。 可在运行环境与资源页面查看准备方案。</div></div>} />}
                <Form.Item name="base_model" label="基础模型" rules={required} extra={<a href="/app/resources">登记本地模型或查看资源状态</a>}><Select options={[{value:'Qwen/Qwen2.5-0.5B-Instruct', label:'Qwen2.5 0.5B 配置模板（以实际检查为准）'}, ...modelResources.filter(item => item.id).map(item => ({value:`managed:${item.id}`, label:`${item.name} · ${item.ready ? '文件已检查' : '待准备'}`, disabled:!item.ready}))]} /></Form.Item>
                <Row gutter={16}>
                  <Col span={12}><Form.Item name="template" label="对话模板" rules={required}><Input /></Form.Item></Col>
                  <Col span={12}><Form.Item name="epochs" label="训练轮数" rules={required}><InputNumber min={0.01} max={100} style={{ width: '100%' }} /></Form.Item></Col>
                  <Col span={12}><Form.Item name="precision" label="训练精度" rules={required}><Select options={[{ value: 'bf16', label: 'BF16' }, { value: 'fp16', label: 'FP16' }]} /></Form.Item></Col>
                  <Col span={12}><Form.Item name="variant" label="训练 / 合并组别" rules={required}><Select options={variantOptions} /></Form.Item></Col>
                </Row>
                <Space wrap>{config.data_version_id ? <Button disabled={disabled} onClick={() => void prepareVersion()}>为候选版本生成训练配置</Button> : actionButton('生成训练配置', 'prepare_configs')}{actionButton('开始训练', 'train', true)}{actionButton('合并模型', 'merge')}</Space>
              </Card> },
              { key: 'evaluation', label: '模型评测', children: <Card title="4 · 统一评测">
                <Alert type={preflight?.evaluation.ready ? 'success' : 'warning'} showIcon message={preflight?.evaluation.ready ? '评测基础条件已检查' : '评测条件尚未满足'} description={<div>{(preflight?.evaluation.checks || []).filter(item => !item.ready).map(item => <div key={item.key}>• {item.message}</div>)}{preflight?.evaluation.ready && !preflight.evaluation.dry_run_ready && <div>请先完成当前配置的评测试运行。</div>}</div>} action={<Button onClick={() => setPreflightRevision(value => value + 1)}>重新检查</Button>} />
                <details><summary>高级评测设置</summary><Form.Item name="eval_workspace" label="评测工作目录" rules={required}><Input /></Form.Item></details>
                <Row gutter={16}>
                  <Col span={12}><Form.Item name="eval_model" label="评测对象" rules={required}><Select options={[{ value: 'all', label: '全部可用模型（含 Base）' }, { value: 'base', label: 'Base' }, ...evaluationOptions]} /></Form.Item></Col>
                  <Col span={12}><Form.Item name="eval_batch_size" label="评测批量大小" rules={required}><InputNumber min={1} max={128} precision={0} style={{ width: '100%' }} /></Form.Item></Col>
                </Row>
                <Form.Item name="eval_max_out_len" label="单题最大输出长度（token）" rules={required} extra="所有模型使用相同上限。调整后请重新生成评测配置，再开始评测。"><InputNumber min={64} max={1024} precision={0} style={{ width: '100%' }} /></Form.Item>
                <Form.Item name="eval_mode" label="评测模式" rules={required} extra="选择快捷档位会填入科目与题量；手动调整后自动切换为自定义。">
                  <Select options={evaluationModeOptions} popupMatchSelectWidth={false} />
                </Form.Item>
                <Form.Item name="eval_subjects" label="评测科目" rules={[{ required: true, type: 'array', min: 1, message: '请至少选择一个评测科目' }]}>
                  <Select mode="multiple" showSearch optionFilterProp="label" maxTagCount="responsive" placeholder="搜索科目中文名或英文名，可跨基准多选"
                    options={['ceval', 'cmmlu'].map(benchmark => ({
                      label: benchmark === 'ceval' ? 'C-Eval（52 科目）' : 'CMMLU（67 科目）',
                      options: evaluationSubjects.filter(subject => subject.benchmark === benchmark).map(subject => ({
                        value: subject.value, label: `${benchmark === 'ceval' ? 'C-Eval' : 'CMMLU'} · ${subject.label}（${subject.value.split(':')[1]}）`,
                      })),
                    }))} />
                </Form.Item>
                <Space wrap style={{ marginTop: -8, marginBottom: 16 }}>
                  <Button size="small" onClick={() => selectSubjects('ceval')}>全选 C-Eval</Button>
                  <Button size="small" onClick={() => selectSubjects('cmmlu')}>全选 CMMLU</Button>
                  <Button size="small" onClick={() => selectSubjects()}>清空科目</Button>
                </Space>
                <Row gutter={16} align="middle">
                  <Col xs={24} sm={12}><Form.Item name="eval_samples_per_subject" label="每科最多题数" rules={config.eval_all_questions ? [] : [{ required: true, type: 'integer', min: 1, max: 10000, message: '请输入 1 到 10000 之间的整数' }]}>
                    <InputNumber min={1} max={10000} precision={0} disabled={busy || submitting || config.eval_all_questions} style={{ width: '100%' }} />
                  </Form.Item></Col>
                  <Col xs={24} sm={12}><Form.Item name="eval_all_questions" valuePropName="checked"><Checkbox>使用所选科目的全部题目</Checkbox></Form.Item></Col>
                </Row>
                <Typography.Paragraph type="secondary" aria-live="polite">
                  已选 {config.eval_subjects.length} 科目，{config.eval_all_questions ? '使用全部题目' : `每科最多 ${config.eval_samples_per_subject ?? 0} 题，每个模型合计最多 ${config.eval_subjects.length * (config.eval_samples_per_subject ?? 0)} 题`}。实际题量以各科题库为准。所有模型使用相同科目与题量，修改后请重新生成评测配置。
                </Typography.Paragraph>
                <Space wrap>
                  {actionButton('生成评测配置', 'make_eval_manifest')}{actionButton('评测试运行', 'eval_dry')}
                  {actionButton('开始评测', 'eval_run', true)}{actionButton('仅重新评分', 'eval_score')}
                </Space>
              </Card> },
              { key: 'results', label: '结果与错误样本', children: <Space orientation="vertical" size="large" style={{ width: '100%' }}>
                <Card title="错误样本回流">
                  <Typography.Paragraph type="secondary">将预测结果中的错误样本整理为 JSONL，供数据清洗和质量评价环节复查。</Typography.Paragraph>
                  <Form.Item name="predictions_path" label="预测结果 JSONL"><Input placeholder="填写后端电脑上的预测结果文件路径" /></Form.Item>
                  <Form.Item name="badcase_model" label="样本所属模型"><Select options={[{ value: 'base', label: 'Base' }, ...variants.slice(1)]} /></Form.Item>
                  <Button disabled={disabled || !(config.predictions_path || '').trim()} onClick={() => void run('export_badcases')}>导出错误样本</Button>
                </Card>
                <Card title="5 · 评测结果" extra={<Space wrap>{actionButton('汇总评测结果', 'compare_results', true)}<Button onClick={() => void refreshResults()}>刷新结果</Button></Space>}>
                  <Space wrap style={{ marginBottom: 16 }}>
                    <Typography.Text>统一测评项目</Typography.Text>
                    <Select aria-label="统一测评项目" showSearch optionFilterProp="label" style={{ width: 440, maxWidth: '100%' }}
                      value={comparisonProject?.value} options={resultProjects} onChange={setSelectedProject}
                      placeholder={rows.length ? '暂无共同测评项目' : '等待评测结果'} disabled={!rows.length} />
                  </Space>
                  <Typography.Paragraph type="secondary">在同一测评项目、同一指标下比较各模型。点击“平均分”表头，可切换由高到低、由低到高或默认顺序。</Typography.Paragraph>
                  <Table<ResultRow> key={comparisonProject?.value ?? 'empty'} size="small" dataSource={comparisonRows} rowKey={row => `${row.model}-${row.benchmark}-${row.metric}`} pagination={{ pageSize: 10 }} scroll={{ x: 700 }} locale={{ emptyText: rows.length ? '暂无所有模型共同完成的测评项目，请先完成相同项目的评测。' : '暂无评测结果。完成评测后，点击“汇总评测结果”。' }} columns={[
                    { title: '模型', dataIndex: 'model' }, { title: '基准', dataIndex: 'benchmark' },
                    { title: '指标', dataIndex: 'metric' }, { title: '次数', dataIndex: 'runs' },
                    {
                      title: '平均分', dataIndex: 'mean_score',
                      sorter: (a, b) => Number(a.mean_score) - Number(b.mean_score),
                      sortDirections: ['descend', 'ascend'],
                      showSorterTooltip: { title: '切换分数排序：由高到低 / 由低到高 / 默认顺序' },
                    },
                    { title: '标准差', dataIndex: 'std_score' },
                    { title: '相对 Base 变化', dataIndex: 'delta_score', render: value => value || '—' },
                  ]} />
                </Card>
              </Space> },
            ]} />
          </Col>
        </Row>
      </Form>
    </div>
  );
}
