import { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Input, Row, Select, Space, Tag, Typography } from 'antd';
import request from '@/services/request';

interface Check { key: string; ready: boolean; message: string }
interface ResourcesResponse {
  data: { assets: number; synthetic_example: boolean };
  templates: Array<{id: string; name: string; description: string; rules: string[]}>;
  models: Array<{id?: string; name: string; ready: boolean; message: string; license_status: string}>;
  environments: Array<{name: string; kind: string; ready: boolean; checks?: Check[]; details?: {message?: string; cuda_state?: string; missing_packages?: string[]; gpus?: string[]}}>;
}

export default function Resources() {
  const [data, setData] = useState<ResourcesResponse | null>(null);
  const [error, setError] = useState('');
  const [checking, setChecking] = useState(false);
  const [modelName, setModelName] = useState(''); const [modelPath, setModelPath] = useState(''); const [license, setLicense] = useState('unverified');
  const refresh = useCallback(() => request.get('/preproject-data/resources').then((value) => { setData(value as unknown as ResourcesResponse); setError(''); }).catch(() => setError('资源状态读取失败，请检查连接后重试。')), []);
  useEffect(() => { void refresh(); }, [refresh]);
  const check = async () => {
    setChecking(true); setError('');
    try { await request.post('/module4/run', {action: 'check_training_env', config: {}}); setError('环境检查已启动，请稍后刷新状态。'); }
    catch { setError('无法启动环境检查，请确认没有其他实验正在运行。'); }
    finally { setChecking(false); }
  };
  const registerModel = async () => {
    try { await request.post('/preproject-data/resources/models', {name: modelName, path: modelPath, license_status: license}); setModelName(''); setModelPath(''); await refresh(); setError('模型资源已登记；模型文件及许可仍需按使用场景确认。'); }
    catch { setError('模型登记失败：请检查目录中的配置、权重和分词器文件。'); }
  };
  return <main style={{maxWidth: 1280, margin: '0 auto', padding: 24}}>
    <Typography.Title level={2}>运行环境与资源</Typography.Title>
    <Typography.Paragraph type="secondary">基础治理使用 CPU；训练、评测资源独立准备，不影响数据治理。</Typography.Paragraph>
    {error && <Alert showIcon type="info" message={error} style={{marginBottom: 16}} />}
    <Space style={{marginBottom: 16}}><Button onClick={() => void refresh()}>刷新状态</Button><Button loading={checking} onClick={() => void check()}>检查训练环境</Button></Space>
    <Row gutter={[16,16]}>{data?.environments.map(env => <Col key={env.kind} xs={24} lg={8}><Card title={env.name} extra={<Tag color={env.ready ? 'success' : 'warning'}>{env.ready ? '已就绪' : '待准备'}</Tag>}>
      <Typography.Paragraph>{env.details?.message || (env.kind === 'cpu' ? '平台内置基础清洗、去重、脱敏和质量评价。' : '请准备独立评测环境和所选题库。')}</Typography.Paragraph>
      {env.details?.gpus?.length ? <p>检测到显卡：{env.details.gpus.join('；')}</p> : null}
      {env.details?.cuda_state === 'not_checked_without_torch' && <p>尚未安装 PyTorch，CUDA 可用性未验证。</p>}
      {env.details?.missing_packages?.length ? <p>缺少依赖：{env.details.missing_packages.join('、')}</p> : null}
      {env.checks && <details><summary>查看准备项</summary>{env.checks.filter(item => !item.ready).map(item => <p key={item.key}>{item.message}</p>)}</details>}
      {env.kind !== 'cpu' && <details><summary>准备说明</summary><p>创建与平台服务分离的 Python 虚拟环境，按项目环境说明安装相应依赖，并准备有权使用的模型或题库。平台不会自动下载大型资源。完成后重新检查。</p></details>}
    </Card></Col>)}</Row>
    <Row gutter={[16,16]} style={{marginTop: 4}}><Col xs={24} lg={12}><Card title="数据和治理模板"><p>已登记数据：{data?.data.assets ?? '—'} 个；合成示例：{data?.data.synthetic_example ? '可用' : '未确认'}</p>{data?.templates.map(item => <p key={item.id}><strong>{item.name}</strong>：{item.description}</p>)}</Card></Col>
      <Col xs={24} lg={12}><Card title="模型资源"><p>模型模板只是配置，实际训练前必须检查权重、分词器及使用许可。</p>{data?.models.map(item => <p key={item.id || item.name}><Tag color={item.ready ? 'success' : 'default'}>{item.ready ? '本地可用' : '待准备'}</Tag>{item.name} · {item.license_status}</p>)}
        <details><summary>登记本地模型</summary><Space direction="vertical" style={{width:'100%', marginTop: 12}}><Input aria-label="模型名称" placeholder="模型名称" value={modelName} onChange={event => setModelName(event.target.value)} /><Input aria-label="本地模型目录" placeholder="模型目录（仅用于资源管理）" value={modelPath} onChange={event => setModelPath(event.target.value)} /><Select aria-label="模型许可状态" value={license} onChange={setLicense} options={[{value:'unverified', label:'许可待核验'}, {value:'user_attested', label:'用户声明已核验'}]} /><Button disabled={!modelName.trim() || !modelPath.trim()} onClick={() => void registerModel()}>验证并登记</Button></Space></details>
      </Card></Col></Row>
  </main>;
}
