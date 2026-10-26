import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert, Button, Card, Checkbox, Col, Form, Input, InputNumber, Row, Select, Space, Table, Tag, Typography, message,
} from 'antd';
import {
  clearModule4Logs, getModule4Results, getModule4Status, runModule4, stopModule4,
} from '@/services/api/module4';
import type { Module4Action, Module4Config, Module4Status, ResultRow } from '@/services/api/module4';
import { evaluationModeOptions, evaluationPreset, evaluationSubjects } from '@/config/module4Evaluation';

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
  eval_workspace: 'D:\\module4_opencompass',
  eval_mode: 'quick',
  ...evaluationPreset('quick')!,
  eval_batch_size: 1,
  eval_max_out_len: 512,
  eval_model: 'all',
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

export default function Module4() {
  const [form] = Form.useForm<Module4Config>();
  const [config, setConfig] = useState(initialConfig);
  const [status, setStatus] = useState<Module4Status | null>(null);
  const [connectionError, setConnectionError] = useState('');
  const [requestError, setRequestError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [revision, setRevision] = useState(0);
  const [rows, setRows] = useState<ResultRow[]>([]);
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
      const values = await form.validateFields();
      setSubmitting(true);
      setRequestError('');
      const result = await runModule4(action, values);
      message.success(result.message);
      setStatus(await getModule4Status());
    } catch (error) {
      if (error instanceof Error) setRequestError('任务未能启动，请查看错误提示并检查参数或运行环境。');
    } finally {
      setSubmitting(false);
    }
  }

  function updateConfig(changed: Partial<Module4Config>, values: Module4Config) {
    const preset = changed.eval_mode && evaluationPreset(changed.eval_mode);
    if (preset) {
      Object.assign(values, preset);
      form.setFieldsValue(preset);
    } else if (['eval_subjects', 'eval_samples_per_subject', 'eval_all_questions'].some(key => key in changed)) {
      values.eval_mode = 'custom';
      form.setFieldValue('eval_mode', 'custom');
    }
    setConfig({ ...values });
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

  const actionButton = (label: string, action: Module4Action, primary = false) => (
    <Button type={primary ? 'primary' : 'default'} disabled={disabled} onClick={() => void run(action)}>{label}</Button>
  );

  return (
    <div className="space-y-6">
      <div>
        <Typography.Title level={2} style={{ marginBottom: 8 }}>数据筛选与模型验证</Typography.Title>
        <Typography.Paragraph type="secondary">
          验证已有数据和模型，尚未提供处理结果的组留空，接入后再参与对比。
        </Typography.Paragraph>
      </div>
      {connectionError && <Alert type="error" title={connectionError} action={<Button onClick={() => setRevision(value => value + 1)}>重新连接</Button>} />}
      {requestError && <Alert type="error" title={requestError} closable onClose={() => setRequestError('')} />}

      <Row gutter={[20, 20]}>
        <Col xs={24} xl={15}>
          <Form form={form} layout="vertical" initialValues={config} onValuesChange={updateConfig} disabled={busy || submitting}>
            <Space orientation="vertical" size="large" style={{ width: '100%' }}>
              <Card title="1 · 运行环境">
                <Typography.Paragraph type="secondary">先检查训练和评测依赖。任务在平台后端所在电脑执行，文件路径也以该电脑为准。</Typography.Paragraph>
                <Form.Item name="training_python" label="训练 Python（可选）" extra="留空时使用后端配置的训练环境或项目内 .venv-lora；也可填写已有环境的 python.exe 完整路径。"><Input placeholder="例如 D:\training-env\Scripts\python.exe" /></Form.Item>
                <Form.Item name="opencompass_env" label="OpenCompass 评测环境" rules={required}><Input /></Form.Item>
                <Space wrap>
                  {actionButton('检查训练环境', 'check_training_env')}
                  {actionButton('修复评测依赖', 'fix_eval_dependencies')}
                  {actionButton('检查评测环境', 'check_eval_env')}
                </Space>
              </Card>
              <Card title="2 · 数据筛选">
                <Typography.Paragraph type="secondary">可按需调整输入文件和每组样本数。</Typography.Paragraph>
                <Form.Item name="raw_path" label="原始候选数据" rules={required}><Input /></Form.Item>
                <Form.Item name="evaluated_path" label="质量评价结果"><Input placeholder="待接入，留空时跳过 Rule、LLM-only、Ours" /></Form.Item>
                <Form.Item name="datajuicer_path" label="Data-Juicer 独立处理结果"><Input placeholder="待接入，留空时跳过 Data-Juicer" /></Form.Item>
                <Space wrap style={{ marginBottom: 16 }}>
                  {variants.filter(option => option.value in pending).map(option => <Tag key={option.value}>{option.label}：待接入</Tag>)}
                </Space>
                <Row gutter={16}>
                  <Col span={12}><Form.Item name="sample_count" label="每组样本数" rules={required}><InputNumber min={1} max={1000000} precision={0} style={{ width: '100%' }} /></Form.Item></Col>
                  <Col span={12}><Form.Item name="seed" label="随机种子" rules={required}><InputNumber min={0} max={2147483647} precision={0} style={{ width: '100%' }} /></Form.Item></Col>
                </Row>
                <Space wrap>{actionButton('生成验证数据', 'build_data', true)}{actionButton('校验数据', 'validate_data')}</Space>
              </Card>
              <Card title="3 · 模型微调与合并">
                <Form.Item name="base_model" label="基础模型" rules={required}><Input /></Form.Item>
                <Row gutter={16}>
                  <Col span={12}><Form.Item name="template" label="对话模板" rules={required}><Input /></Form.Item></Col>
                  <Col span={12}><Form.Item name="epochs" label="训练轮数" rules={required}><InputNumber min={0.01} max={100} style={{ width: '100%' }} /></Form.Item></Col>
                  <Col span={12}><Form.Item name="precision" label="训练精度" rules={required}><Select options={[{ value: 'bf16', label: 'BF16' }, { value: 'fp16', label: 'FP16' }]} /></Form.Item></Col>
                  <Col span={12}><Form.Item name="variant" label="训练 / 合并组别" rules={required}><Select options={variantOptions} /></Form.Item></Col>
                </Row>
                <Space wrap>{actionButton('生成训练配置', 'prepare_configs')}{actionButton('开始训练', 'train', true)}{actionButton('合并模型', 'merge')}</Space>
              </Card>
              <Card title="4 · 统一评测">
                <Form.Item name="eval_workspace" label="评测工作目录（纯英文路径）" rules={required}><Input /></Form.Item>
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
              </Card>
              <Card title="错误样本回流">
                <Typography.Paragraph type="secondary">将预测结果中的错误样本整理为 JSONL，供数据清洗和质量评价环节复查。</Typography.Paragraph>
                <Form.Item name="predictions_path" label="预测结果 JSONL"><Input placeholder="填写后端电脑上的预测结果文件路径" /></Form.Item>
                <Form.Item name="badcase_model" label="样本所属模型"><Select options={[{ value: 'base', label: 'Base' }, ...variants.slice(1)]} /></Form.Item>
                <Button disabled={disabled || !config.predictions_path.trim()} onClick={() => void run('export_badcases')}>导出错误样本</Button>
              </Card>
            </Space>
          </Form>
        </Col>
        <Col xs={24} xl={9}>
          <div style={{ position: 'sticky', top: 0 }}>
            <Card title="任务状态" extra={<Tag color={busy ? 'processing' : status?.task.status === 'failed' ? 'error' : 'default'}>{status ? statuses[status.task.status] : '连接中'}</Tag>}>
              <Typography.Paragraph>{status?.task.label || '正在连接任务服务…'}</Typography.Paragraph>
              <Typography.Paragraph type="secondary">同一时刻运行一个任务。离开此页面后任务继续执行，可随时返回查看。</Typography.Paragraph>
              <Space wrap style={{ marginBottom: 16 }}>
                <Button danger disabled={!busy || submitting || status?.task.status === 'stopping'} onClick={() => void stop()}>停止当前任务</Button>
                <Button disabled={!status || busy} onClick={() => void clear()}>清空日志</Button>
              </Space>
              <pre ref={logRef} aria-label="任务日志" aria-live="off" style={{ height: 360, overflow: 'auto', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', background: '#191f2b', color: '#d6e0ef', padding: 16, borderRadius: 8, fontSize: 12, margin: 0 }}>{status?.task.logs || '任务开始后，运行日志将显示在这里。'}</pre>
              {status?.task.exit_code != null && <Typography.Text type="secondary">退出码：{status.task.exit_code}</Typography.Text>}
            </Card>
            <Card title="实验进度" style={{ marginTop: 20 }}>
              <Space wrap>
                {progress.map(({ key, label, completed }) => (
                  <Tag key={key} color={completed ? 'success' : 'default'} title={completed ? '本次任务已成功完成，产物已就绪' : '本次任务尚未完成'}>{label}{completed ? ' ✓' : ''}</Tag>
                ))}
              </Space>
            </Card>
          </div>
        </Col>
        <Col span={24}>
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
        </Col>
      </Row>
    </div>
  );
}
