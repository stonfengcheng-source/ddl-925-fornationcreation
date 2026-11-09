import request from '@/services/request';

export interface BaselineVersion { version_id: string; dataset_id?: string; sample_count: number; compatible: boolean; reason: string; is_default?: boolean; label_distribution?: Record<string, number>; governance_status?: string; }
export interface BaselineMetrics { accuracy: number; macro_f1: number; confusion_matrix: number[][]; classes: string[]; train_count: number; test_count: number; dataset_count: number; duration_seconds: number; }
export interface BaselineExperiment {
  experiment_id: string; version_id: string; dataset_id?: string; status: 'pending'|'running'|'completed'|'failed';
  created_at: string; error?: string | null; seed: number; test_size: number; sample_count: number;
  metrics?: BaselineMetrics; errors?: Array<{sample_id:string;text:string;actual:string;predicted:string}>; logs?: string[]; files: string[];
}
export const baselineEnvironment = () => request.get('/baseline/environment') as Promise<{ready:boolean;message:string;python?:string;sklearn?:string}>;
export const baselineVersions = () => request.get('/baseline/versions') as Promise<{items:BaselineVersion[]}>;
export const baselineExperiments = () => request.get('/baseline/experiments') as Promise<{items:BaselineExperiment[]}>;
export const baselineExperiment = (id:string, signal?:AbortSignal) => request.get(`/baseline/experiments/${id}`, {signal}) as Promise<BaselineExperiment>;
export const createBaselineExperiment = (version_id:string, seed:number, test_size:number) => request.post('/baseline/experiments', {version_id,seed,test_size}) as Promise<BaselineExperiment>;
export const prepareDefaultBaseline = () => request.post('/baseline/prepare-default') as Promise<{version_id:string; sample_count:number; reused:boolean}>;
export async function downloadBaselineExperiment(id:string, filename:string): Promise<void> {
  const blob = await request.get(`/baseline/experiments/${id}/files/${encodeURIComponent(filename)}`, {responseType:'blob'}) as unknown as Blob;
  const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = filename; link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
