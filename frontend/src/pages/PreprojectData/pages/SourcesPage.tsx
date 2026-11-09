import * as React from 'react';
import { Alert, Button, Card, Collapse, Empty, Input, Modal, Space, Tag, Typography } from 'antd';
import { getLocalEduChatStatus, importLocalEduChat, previewPreprojectSource, uploadPreprojectSource, validatePreprojectSource } from '@/services/api/preprojectData';
import { useWorkspace } from '../layout/PreprojectLayout';

export function SourcesPage() {
  const { sources, sourceId, chooseSource, go, refreshSources } = useWorkspace();
  const [file, setFile] = React.useState<File | null>(null);
  const [error, setError] = React.useState(''); const [notice, setNotice] = React.useState('');
  const [busy, setBusy] = React.useState(false); const [showImport, setShowImport] = React.useState(false);
  const [preview, setPreview] = React.useState<Array<Record<string, string>>>([]);
  const [localAvailable, setLocalAvailable] = React.useState(false);
  const [validatedSource, setValidatedSource] = React.useState(() => sessionStorage.getItem('pp-validated-source') || '');
  const [metadata, setMetadata] = React.useState({dataset_id:'', source_url:'', license:'', revision:'', split:'local'});
  const example = sources.find(item => item.is_platform_default && item.default_ready);
  const selected = sources.find(item => item.source_id === sourceId);
  const validated = Boolean(selected && (((selected.is_platform_default || selected.is_classification_dataset) && selected.default_ready) || validatedSource === selected.source_id));
  React.useEffect(() => { let active = true; setPreview([]); if (sourceId) previewPreprojectSource(sourceId, 0, 3).then(data => { if (active) setPreview(data.samples); }).catch(() => { if (active) setError('样本预览加载失败，可重新选择数据。'); }); return () => {active=false;}; }, [sourceId]);
  React.useEffect(() => { let active = true; getLocalEduChatStatus().then(value => { if (active) setLocalAvailable(value.available); }).catch(() => undefined); return () => {active=false;}; }, []);
  const upload = async () => { if (!file) return; setBusy(true); setError(''); try { const result = await uploadPreprojectSource(file, {...metadata, dataset_id:metadata.dataset_id || file.name, source_url:metadata.source_url || 'user-provided', license:metadata.license || 'unverified', revision:metadata.revision || 'unverified'}); refreshSources(); chooseSource(result.source_id); setShowImport(false); setNotice(`已导入 ${result.sample_count} 条，请验证数据并核验来源许可。`); } catch { setError('导入失败，请检查文件格式和来源信息。'); } finally { setBusy(false); } };
  const restore = async () => { setBusy(true); setError(''); try { const result = await importLocalEduChat(); refreshSources(); chooseSource(result.source_id); setNotice(`已登记研究数据：${result.sample_count} 条；来源及许可仍待核验。`); } catch { setError('研究数据登记失败，请检查文件及来源清单。'); } finally { setBusy(false); } };
  const validate = async () => { setError(''); try { const value = await validatePreprojectSource(sourceId); const accepted = value.valid ? sourceId : ''; setValidatedSource(accepted); sessionStorage.setItem('pp-validated-source', accepted); setNotice(value.message || (value.valid ? '验证通过' : '验证未通过')); } catch { setError('验证失败，请检查数据并重试。'); } };
  return <div className="space-y-5">
    {error && <Alert type="error" showIcon message={error} closable onClose={() => setError('')} />}
    {notice && <Alert type="info" showIcon message={notice} closable onClose={() => setNotice('')} />}
    <Card className="governance-feature" bordered={false}>
      <div className="governance-feature-grid"><div><Tag color="blue">平台内置数据</Tag><Typography.Title level={3}>教育问答基础数据集</Typography.Title>
        <Typography.Paragraph>选择数据后，可查看内容并配置清洗、去重、隐私保护与质量评价规则。</Typography.Paragraph>
        <Typography.Text type="secondary">合成数据 · 用于功能验证{example ? ` · ${example.sample_count} 条` : ' · 待准备'}</Typography.Text>
      </div><div><Tag color={example ? 'success' : 'default'}>{example ? '数据与规则已就绪' : '数据待准备'}</Tag></div></div>
    </Card>
    <Card title="选择已有数据" extra={<Space><Button onClick={() => setShowImport(true)}>导入新数据</Button>{localAvailable && <Button onClick={() => void restore()} loading={busy}>导入已有研究数据</Button>}</Space>}>
      <Typography.Paragraph type="secondary">示例和真实数据分别管理，来源及许可状态独立核验。</Typography.Paragraph>
      <div className="governance-source-grid">{sources.filter(item => item.source_type !== 'test_fixture' || ((item.is_platform_default || item.is_classification_dataset) && item.default_ready)).map(item => <Card key={item.source_id} size="small" hoverable className={sourceId === item.source_id ? 'governance-selected' : ''} onClick={() => chooseSource(item.source_id)}>
        <Space wrap><Typography.Text strong>{item.is_platform_default ? '教育问答基础数据集' : item.dataset_id}</Typography.Text><Tag color={item.is_platform_default || item.is_classification_dataset ? 'blue' : 'default'}>{item.is_platform_default || item.is_classification_dataset ? '平台合成数据' : '我的数据'}</Tag></Space>
        <p>{item.sample_count} 条 · {(item.is_platform_default || item.is_classification_dataset) && item.default_ready ? '已验证，可直接开始' : '请验证后治理'}</p>
      </Card>)}</div>
      {!sources.length && <Empty description="暂无数据，您可以从上方示例开始" />}
      {selected && <div className="governance-next"><Typography.Text>当前数据：{selected.is_platform_default ? '教育问答基础数据集' : selected.dataset_id} · {selected.sample_count} 条</Typography.Text><Space>{!(selected.is_platform_default || selected.is_classification_dataset) && <Button onClick={() => void validate()}>验证数据源</Button>}<Button type="primary" disabled={!validated} onClick={() => go('pipelines')}>下一步：治理配置</Button></Space></div>}
      {selected && !validated && <Typography.Text type="secondary">请先验证选中的数据。</Typography.Text>}
      {preview.length > 0 && <Collapse size="small" items={[{key:'preview', label:'查看脱敏样本', children:preview.map(row => <div key={row.sample_id}><p><b>问题：</b>{row.instruction}</p><p><b>回答：</b>{row.output}</p></div>)}]} />}
    </Card>
    <Modal title="导入数据资产" open={showImport} onCancel={() => setShowImport(false)} onOk={() => void upload()} okText="导入数据" okButtonProps={{disabled:!file, loading:busy}}>
      <p>选择有权使用的文件。文本文件按非空行读取，问答数据支持 JSONL。</p><input aria-label="数据文件" type="file" accept=".txt,.json,.jsonl,.parquet,.pq" onChange={event => setFile(event.target.files?.[0] || null)} />
      <Collapse style={{marginTop:16}} items={[{key:'metadata',label:'来源高级设置（选填）',children:(['dataset_id','source_url','license','revision','split'] as const).map(key => <label key={key} style={{display:'block',marginBottom:10}}>{({dataset_id:'数据集名称',source_url:'来源链接',license:'许可',revision:'版本',split:'数据分片'})[key]}<Input aria-label={key} value={metadata[key]} onChange={event => setMetadata({...metadata,[key]:event.target.value})} /></label>)}]} />
      <p>未核验的来源不会自动获得发布或训练授权。</p>
    </Modal>
  </div>;
}
