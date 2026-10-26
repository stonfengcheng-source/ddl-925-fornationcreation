import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import Module4 from './index';
import { getModule4Results, getModule4Status, runModule4, stopModule4 } from '@/services/api/module4';
import type { Module4Status, ResultRow } from '@/services/api/module4';

vi.mock('@/services/api/module4', () => ({
  getModule4Status: vi.fn(), getModule4Results: vi.fn(),
  runModule4: vi.fn(), stopModule4: vi.fn(), clearModule4Logs: vi.fn(),
}));
vi.mock('antd', async (importOriginal) => ({
  ...await importOriginal<typeof import('antd')>(),
  message: { success: vi.fn(), info: vi.fn() },
}));

const idle: Module4Status = {
  task: { status: 'idle', label: '尚未运行任务', logs: '', exit_code: null, started_at: null, finished_at: null },
  artifacts: {},
};

const scoreRow = (model: string, benchmark: string, mean_score: string, metric = 'accuracy'): ResultRow => ({
  model, benchmark, mean_score, metric, runs: '1', std_score: '0', base_mean_score: '', delta_score: '',
});

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', class {
    observe() {}
    unobserve() {}
    disconnect() {}
  });
  vi.clearAllMocks();
  localStorage.clear();
  vi.mocked(getModule4Status).mockResolvedValue(idle);
  vi.mocked(getModule4Results).mockResolvedValue({ rows: [] });
  vi.mocked(runModule4).mockResolvedValue({ message: '已启动' });
  vi.mocked(stopModule4).mockResolvedValue({ message: '已发送停止请求' });
});
afterEach(cleanup);

describe('平台内模型验证页面', () => {
  it('小样本结果不再显示已删除的提示', async () => {
    localStorage.setItem('module4.platform.config', JSON.stringify({ sample_count: 2000 }));
    vi.mocked(getModule4Results).mockResolvedValue({
      rows: [{ model: 'ours', benchmark: 'ceval_macro', metric: 'accuracy', runs: '1', mean_score: '35', std_score: '0', base_mean_score: '33', delta_score: '2' }],
      metadata: { sample_count: 4 },
    });
    render(<Module4 />);
    await screen.findByText('35');
    expect(screen.queryByText('这份结果来自每组 4 条的小样本测试')).not.toBeInTheDocument();
  });

  it('点击平均分表头按数值降序、升序排序，并可恢复默认顺序', async () => {
    vi.mocked(getModule4Results).mockResolvedValue({ rows: [
      { model: 'raw', mean_score: '9.5' },
      { model: 'ours', mean_score: '100' },
      { model: 'rule', mean_score: '80' },
    ].map(row => ({ ...row, benchmark: 'ceval_macro', metric: 'accuracy', runs: '1', std_score: '0', base_mean_score: '', delta_score: '' })) });
    render(<Module4 />);
    await screen.findByText('9.5');
    const table = within(screen.getByText('5 · 评测结果').closest('.ant-card')!);
    const models = () => table.getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell')[0].textContent);
    expect(models()).toEqual(['raw', 'ours', 'rule']);
    fireEvent.click(table.getByRole('columnheader', { name: '平均分' }));
    expect(models()).toEqual(['ours', 'rule', 'raw']);
    fireEvent.click(table.getByRole('columnheader', { name: '平均分' }));
    expect(models()).toEqual(['raw', 'rule', 'ours']);
    fireEvent.click(table.getByRole('columnheader', { name: '平均分' }));
    expect(models()).toEqual(['raw', 'ours', 'rule']);
  });

  it('默认比较统一总体平均，切换项目后只在同一科目内排序', async () => {
    vi.mocked(getModule4Results).mockResolvedValue({ rows: [
      scoreRow('base', 'overall_macro', '33.581871', 'macro_average'),
      scoreRow('raw', 'overall_macro', '34.000000', 'macro_average'),
      scoreRow('base', 'ceval-computer_network', '31.000000'),
      scoreRow('raw', 'ceval-computer_network', '36.000000'),
      scoreRow('base', 'cmmlu-college_education', '40.000000'),
      scoreRow('raw', 'cmmlu-college_education', '35.000000'),
      scoreRow('base', 'base_only_project', '99.000000'),
    ] });
    render(<Module4 />);
    await screen.findByText('33.581871');
    const table = within(screen.getByText('5 · 评测结果').closest('.ant-card')!);
    const column = (index: number) => table.getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell')[index].textContent);
    expect(column(1)).toEqual(['overall_macro', 'overall_macro']);
    expect(table.queryByText('99.000000')).not.toBeInTheDocument();
    fireEvent.mouseDown(screen.getByRole('combobox', { name: '统一测评项目' }));
    fireEvent.click(await screen.findByText('ceval-computer_network · accuracy'));
    await waitFor(() => expect(column(1)).toEqual(['ceval-computer_network', 'ceval-computer_network']));
    fireEvent.click(table.getByRole('columnheader', { name: '平均分' }));
    expect(column(0)).toEqual(['raw', 'base']);
    expect(table.queryByText('40.000000')).not.toBeInTheDocument();
  });

  it.each([
    ['ceval-computer_network', 'accuracy', 'cmmlu-college_education', 'accuracy'],
    ['ceval-computer_network', 'accuracy', 'ceval-computer_network', 'f1'],
  ])('科目或指标不一致时不混排比较（%s/%s 与 %s/%s）', async (baseBenchmark, baseMetric, rawBenchmark, rawMetric) => {
    vi.mocked(getModule4Results).mockResolvedValue({ rows: [
      scoreRow('base', baseBenchmark, '20.000000', baseMetric),
      scoreRow('raw', rawBenchmark, '60.000000', rawMetric),
    ] });
    render(<Module4 />);
    await screen.findByText('暂无所有模型共同完成的测评项目，请先完成相同项目的评测。');
    expect(screen.queryByText('20.000000')).not.toBeInTheDocument();
    expect(screen.queryByText('60.000000')).not.toBeInTheDocument();
  });

  it('各项独立判断，环境检查未完成不影响已有数据和配置标绿', async () => {
    vi.mocked(getModule4Status).mockResolvedValue({
      ...idle, artifacts: { environment_report: false, datasets: true, validation: true, configs: true },
      progress: { environment_report: false, datasets: true, validation: true, configs: true },
    });
    render(<Module4 />);
    await screen.findByText('等待任务');
    const progress = within(screen.getByText('实验进度').closest('.ant-card')!);
    expect(progress.getByText('环境检查')).not.toHaveClass('ant-tag-success');
    expect(progress.getByText('训练数据 ✓')).toHaveClass('ant-tag-success');
    expect(progress.getByText('数据校验 ✓')).toHaveClass('ant-tag-success');
    expect(progress.getByText('训练配置 ✓')).toHaveClass('ant-tag-success');
  });

  it('中间步骤未完成时，后续已有产物的步骤仍然标绿', async () => {
    vi.mocked(getModule4Status).mockResolvedValue({
      ...idle, artifacts: { environment_report: true, datasets: true, validation: false, configs: true },
      progress: { environment_report: true, datasets: true, validation: false, configs: true },
    });
    render(<Module4 />);
    await screen.findByText('等待任务');
    const progress = within(screen.getByText('实验进度').closest('.ant-card')!);
    expect(progress.getByText('环境检查 ✓')).toHaveClass('ant-tag-success');
    expect(progress.getByText('训练数据 ✓')).toHaveClass('ant-tag-success');
    expect(progress.getByText('数据校验')).not.toHaveClass('ant-tag-success');
    expect(progress.getByText('训练配置 ✓')).toHaveClass('ant-tag-success');
  });

  it('多模型阶段需自身成员全部就绪，但不阻止其他阶段标绿', async () => {
    vi.mocked(getModule4Status).mockResolvedValue({
      ...idle, artifacts: {
        environment_report: true, datasets: true, validation: true, configs: true,
        checkpoints: { raw: true, rule: false, llm_only: true, datajuicer: true, ours: true },
        merged: { raw: true, rule: true, llm_only: true, datajuicer: true, ours: true },
        eval_manifest: true, summary: true,
      },
      progress: {
        environment_report: true, datasets: true, validation: true, configs: true,
        checkpoints: { raw: true, rule: false, llm_only: true, datajuicer: true, ours: true },
        merged: { raw: true, rule: true, llm_only: true, datajuicer: true, ours: true },
        eval_manifest: true, summary: true,
      },
    });
    render(<Module4 />);
    await screen.findByText('等待任务');
    const progress = within(screen.getByText('实验进度').closest('.ant-card')!);
    expect(progress.getByText('训练配置 ✓')).toHaveClass('ant-tag-success');
    expect(progress.getByText('微调模型')).not.toHaveClass('ant-tag-success');
    expect(progress.getByText('合并模型 ✓')).toHaveClass('ant-tag-success');
    expect(progress.getByText('结果汇总 ✓')).toHaveClass('ant-tag-success');
  });

  it('停止任务后，仅有历史产物不能标绿', async () => {
    vi.mocked(getModule4Status).mockResolvedValue({
      ...idle, task: { ...idle.task, status: 'stopped', label: '检查训练环境' },
      artifacts: { environment_report: true, datasets: true, validation: true, configs: true },
      progress: { environment_report: false, datasets: false, validation: false, configs: false },
    });
    render(<Module4 />);
    await screen.findByText('已停止');
    expect(screen.getByText('实验进度').closest('.ant-card')!.querySelectorAll('.ant-tag-success')).toHaveLength(0);
  });

  it('改变参数后，旧参数的完成记录不能标绿', async () => {
    vi.mocked(getModule4Status).mockResolvedValue({
      ...idle, artifacts: { environment_report: true, datasets: true, validation: true },
      progress: { environment_report: true, datasets: true, validation: true },
      progress_parameters: { datasets: { sample_count: 4 }, validation: { sample_count: 4 } },
    });
    render(<Module4 />);
    await screen.findByText('等待任务');
    const progress = within(screen.getByText('实验进度').closest('.ant-card')!);
    expect(progress.getByText('环境检查 ✓')).toHaveClass('ant-tag-success');
    expect(progress.getByText('训练数据')).not.toHaveClass('ant-tag-success');
    expect(progress.getByText('数据校验')).not.toHaveClass('ant-tag-success');
  });

  it('将生成数据按钮连接到真实 API 服务层并提交表单参数', async () => {
    localStorage.setItem('module4.platform.config', JSON.stringify({
      raw_path: 'D:\\国创\\旧项目\\test_data\\raw_test.jsonl', evaluated_path: 'D:\\国创\\旧项目\\test_data\\quality_eval_test.jsonl',
      datajuicer_path: 'D:\\国创\\旧项目\\test_data\\datajuicer_test.jsonl', sample_count: 4,
    }));
    render(<Module4 />);
    expect(screen.getByLabelText('原始候选数据')).toHaveValue('demo-datasets/education-synthetic/raw_5k.jsonl');
    expect(screen.queryByText('当前每组 4 条，仅用于流程验证')).not.toBeInTheDocument();
    expect(screen.getByLabelText('质量评价结果')).toHaveValue('');
    expect(screen.getByLabelText('Data-Juicer 独立处理结果')).toHaveValue('');
    expect(screen.getByText('Rule：待接入')).toBeInTheDocument();
    expect(screen.getByText('Ours：待接入')).toBeInTheDocument();
    const button = screen.getByText('生成验证数据').closest('button');
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);
    await waitFor(() => expect(runModule4).toHaveBeenCalledWith('build_data', expect.objectContaining({
      sample_count: 100, raw_path: 'demo-datasets/education-synthetic/raw_5k.jsonl', seed: 42,
      evaluated_path: '', datajuicer_path: '',
    })));
  });

  it('统一输出上限默认 512，并将修改后的上限提交给评测配置', async () => {
    render(<Module4 />);
    const limit = screen.getByLabelText('单题最大输出长度（token）');
    expect((limit as HTMLInputElement).value).toBe('512');
    const button = screen.getByText('生成评测配置').closest('button');
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.change(limit, { target: { value: '1024' } });
    fireEvent.blur(limit);
    fireEvent.click(button!);
    await waitFor(() => expect(runModule4).toHaveBeenCalledWith('make_eval_manifest', expect.objectContaining({ eval_max_out_len: 1024 })));
  });

  it('切换快捷档位填入科目和题量，手动改题量后提交自定义配置', async () => {
    render(<Module4 />);
    expect(screen.getByText(/已选 4 科目.*最多 40 题/)).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByRole('combobox', { name: '评测模式' }));
    fireEvent.click(await screen.findByText('标准测试 · 8 科目，每科最多 20 题（共最多 160 题）'));
    expect(screen.getByLabelText('每科最多题数')).toHaveValue('20');
    expect(screen.getByText(/已选 8 科目.*最多 160 题/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('每科最多题数'), { target: { value: '7' } });
    fireEvent.blur(screen.getByLabelText('每科最多题数'));
    expect(screen.getByRole('combobox', { name: '评测模式' }).closest('.ant-select')).toHaveTextContent('自定义 · 自选科目与题量');
    const button = screen.getByRole('button', { name: '生成评测配置' });
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);
    await waitFor(() => expect(runModule4).toHaveBeenCalledWith('make_eval_manifest', expect.objectContaining({
      eval_mode: 'custom', eval_samples_per_subject: 7, eval_all_questions: false,
      eval_subjects: expect.arrayContaining(['ceval:computer_network', 'cmmlu:computer_security']),
    })));
  }, 15000);

  it('可清空后重新选择科目，并提交所选科目的全部题目', async () => {
    render(<Module4 />);
    const button = screen.getByRole('button', { name: '生成评测配置' });
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: '清空科目' }));
    fireEvent.click(button);
    await screen.findByText('请至少选择一个评测科目');
    expect(runModule4).not.toHaveBeenCalled();
    fireEvent.mouseDown(screen.getByRole('combobox', { name: '评测科目' }));
    fireEvent.change(screen.getByRole('combobox', { name: '评测科目' }), { target: { value: 'computer_network' } });
    fireEvent.click(await screen.findByText('C-Eval · 计算机网络（computer_network）'));
    fireEvent.keyDown(screen.getByRole('combobox', { name: '评测科目' }), { key: 'Escape', code: 'Escape' });
    fireEvent.click(screen.getByRole('checkbox', { name: '使用所选科目的全部题目' }));
    expect(screen.getByLabelText('每科最多题数')).toBeDisabled();
    fireEvent.click(button);
    await waitFor(() => expect(runModule4).toHaveBeenCalledWith('make_eval_manifest', expect.objectContaining({
      eval_mode: 'custom', eval_subjects: ['ceval:computer_network'], eval_all_questions: true,
    })));
  }, 15000);

  it('恢复已保存的自选科目与题量，旧版快捷档位自动补全新参数', async () => {
    localStorage.setItem('module4.platform.config', JSON.stringify({ eval_mode: 'custom', eval_subjects: ['cmmlu:education'], eval_samples_per_subject: 12 }));
    const view = render(<Module4 />);
    expect(screen.getByText(/已选 1 科目.*最多 12 题/)).toBeInTheDocument();
    view.unmount();
    localStorage.setItem('module4.platform.config', JSON.stringify({ eval_mode: 'standard' }));
    render(<Module4 />);
    expect(screen.getByText(/已选 8 科目.*最多 160 题/)).toBeInTheDocument();
  });

  it('重新进入页面后显示后台任务，禁止重复启动并可以停止', async () => {
    vi.mocked(getModule4Status).mockResolvedValue({
      ...idle, task: { ...idle.task, status: 'running', label: 'LoRA 训练', logs: '正在训练' },
    });
    render(<Module4 />);
    await screen.findByText('LoRA 训练');
    expect(screen.getByLabelText('任务日志')).toHaveTextContent('正在训练');
    expect(screen.getByText('开始训练').closest('button')).toBeDisabled();
    fireEvent.click(screen.getByText('停止当前任务'));
    await waitFor(() => expect(stopModule4).toHaveBeenCalledOnce());
  });

  it('服务不可用时展示重连入口并禁止任务启动', async () => {
    vi.mocked(getModule4Status).mockRejectedValue(new Error('offline'));
    render(<Module4 />);
    await screen.findByText(/无法连接任务服务/);
    expect(screen.getByText('生成验证数据').closest('button')).toBeDisabled();
    vi.mocked(getModule4Status).mockResolvedValue(idle);
    fireEvent.click(screen.getByText('重新连接'));
    await waitFor(() => expect(screen.getByText('生成验证数据').closest('button')).toBeEnabled());
  });
});
