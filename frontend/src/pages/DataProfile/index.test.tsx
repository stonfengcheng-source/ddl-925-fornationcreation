import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import DataAssets from './index';

vi.mock('@/store/useUserStore', () => ({useUserStore: (selector: (state:unknown)=>unknown) => selector({user:{role:'admin'}})}));
vi.mock('@/services/request', () => ({default:{get: vi.fn((url:string) => Promise.resolve(url === '/datasets/my' ? {data:[
  {id:'a',name:'平台合成示例',tags:['preproject','synthetic_example'],data_type:'json',row_count:34,column_count:2,status:'ready'},
  {id:'b',name:'平台合成示例',tags:['preproject','synthetic_example'],data_type:'json',row_count:32,column_count:2,status:'ready'},
  {id:'c',name:'教育文本分类基础数据集',tags:['preproject','synthetic_classification'],data_type:'json',row_count:54,column_count:3,status:'ready'},
]} : {items:[{source_id:'a',version_count:4,governed_count:3,latest_status:'completed'},{source_id:'b',version_count:4,governed_count:3,latest_status:'completed'},{source_id:'c',version_count:1,governed_count:0,latest_status:null}]}))}}));
describe('数据资产', () => {
  it('聚合同一内置数据集的历史资产并保留独立分类数据', async () => {
    render(<MemoryRouter><DataAssets /></MemoryRouter>);
    expect(await screen.findByText('教育问答基础数据集')).toBeInTheDocument();
    expect(screen.getAllByText('教育问答基础数据集')).toHaveLength(1);
    expect(screen.getByText('教育文本分类基础数据集')).toBeInTheDocument();
    expect(screen.getByText('已治理版本')).toBeInTheDocument();
  });
});
