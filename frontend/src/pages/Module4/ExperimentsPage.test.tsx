import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ExperimentsPage from './ExperimentsPage';
import * as api from '@/services/api/baseline';

vi.mock('./index', () => ({default: () => <div>高级大模型实验</div>}));
vi.mock('@/services/api/baseline', () => ({baselineEnvironment:vi.fn(), baselineExperiments:vi.fn(), baselineExperiment:vi.fn(), baselineVersions:vi.fn(), createBaselineExperiment:vi.fn(), downloadBaselineExperiment:vi.fn(), prepareDefaultBaseline:vi.fn()}));
const version = {version_id:'v1', dataset_id:'教育分类', sample_count:54, compatible:true, reason:'标签已检查'};
const result = {experiment_id:'job1',version_id:'v1',dataset_id:'教育分类',status:'completed' as const,created_at:'now',seed:42,test_size:.25,sample_count:54,files:['report.md'],logs:['Model fit completed'],errors:[{sample_id:'x',text:'分类文本',actual:'math',predicted:'science'}],metrics:{accuracy:.7,macro_f1:.68,confusion_matrix:[[3,1],[0,4]],classes:['math','science'],train_count:40,test_count:14,dataset_count:54,duration_seconds:.5}};
beforeEach(() => {
  vi.clearAllMocks(); vi.stubGlobal('ResizeObserver',class {observe() {} unobserve() {} disconnect() {}});
  vi.mocked(api.baselineEnvironment).mockResolvedValue({ready:true,message:'可用'});
  vi.mocked(api.baselineVersions).mockResolvedValue({items:[version]});
  vi.mocked(api.baselineExperiments).mockResolvedValue({items:[result]});
  vi.mocked(api.baselineExperiment).mockResolvedValue(result);
  vi.mocked(api.createBaselineExperiment).mockResolvedValue(result);
  vi.mocked(api.downloadBaselineExperiment).mockResolvedValue();
});
describe('轻量训练实验', () => {
  it('自动选中合格基础分类版本，并解释其他不兼容版本', async () => {
    vi.mocked(api.baselineVersions).mockResolvedValue({items:[{...version,is_default:true,governance_status:'已完成',label_distribution:{mathematics:18,language:18,science:18}},{...version,version_id:'qa',dataset_id:'EduChat',compatible:false,reason:'问答数据缺少监督分类标签'}]});
    render(<MemoryRouter><ExperimentsPage /></MemoryRouter>);
    fireEvent.click(await screen.findByText('新建训练实验'));
    const button = await screen.findByRole('button',{name:'开始训练'});
    await waitFor(() => expect(button).toBeEnabled());
    expect(screen.getByText(/数学 18 条/)).toBeInTheDocument();
    expect(screen.getByText(/问答数据缺少监督分类标签/)).toBeInTheDocument();
    fireEvent.click(button);
    await waitFor(() => expect(api.createBaselineExperiment).toHaveBeenCalledWith('v1',42,.25));
  });
  it('选择已治理版本创建训练，并展示真实指标和错误样本', async () => {
    render(<MemoryRouter initialEntries={['/app/model-experiments?data_version_id=v1']}><ExperimentsPage /></MemoryRouter>);
    const button = await screen.findByRole('button',{name:'开始训练'});
    await waitFor(() => expect(button).toBeEnabled()); fireEvent.click(button);
    await waitFor(() => expect(api.createBaselineExperiment).toHaveBeenCalledWith('v1',42,.25));
    expect(await screen.findByText('混淆矩阵')).toBeInTheDocument();
    expect(screen.getByText('Macro-F1')).toBeInTheDocument();
    expect(screen.getByText('分类文本')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'下载 report.md'}));
    expect(api.downloadBaselineExperiment).toHaveBeenCalledWith('job1','report.md');
  });
  it('环境未就绪时阻止训练并给出准备入口', async () => {
    vi.mocked(api.baselineEnvironment).mockResolvedValue({ready:false,message:'轻量环境待准备'});
    render(<MemoryRouter initialEntries={['/app/model-experiments?data_version_id=v1']}><ExperimentsPage /></MemoryRouter>);
    expect(await screen.findByText(/轻量环境待准备/)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'开始训练'})).toBeDisabled();
  });
  it('创建失败时允许修改配置并重试', async () => {
    vi.mocked(api.createBaselineExperiment).mockRejectedValueOnce(new Error('offline'));
    render(<MemoryRouter initialEntries={['/app/model-experiments?data_version_id=v1']}><ExperimentsPage /></MemoryRouter>);
    const button = await screen.findByRole('button',{name:'开始训练'});
    await waitFor(() => expect(button).toBeEnabled()); fireEvent.click(button);
    expect(await screen.findByText(/实验启动失败/)).toBeInTheDocument();
    await waitFor(() => expect(button).toBeEnabled());
  });
  it('历史记录可重新读取结果', async () => {
    render(<MemoryRouter><ExperimentsPage /></MemoryRouter>);
    fireEvent.click(await screen.findByRole('button',{name:/教育分类 · 已完成/}));
    expect(await screen.findByText('混淆矩阵')).toBeInTheDocument();
    expect(api.baselineExperiment).toHaveBeenCalledWith('job1');
  });
});
