import request from '@/services/request';
import type { TaskResults, SamplePage, VersionComparison, Statistics } from '@/pages/PreprojectData/types';

export interface PreprojectSource {
  source_id: string;
  dataset_id: string;
  source_url: string;
  license: string;
  revision: string;
  split: string;
  sample_count: number;
  file_sha256: string;
  file_size_bytes: number;
  field_names: string[];
  acquired_at: string;
  revision_verified: boolean;
  license_verified: boolean;
  source_type?: string;
  license_verification_status?: string;
  revision_verification_status?: string;
  version_id?: string;
  status?: string;
  is_platform_default?: boolean;
  default_ready?: boolean;
  is_classification_dataset?: boolean;
}

export interface PreprojectTask {
  task_id: string;
  source_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  current_step: string;
  processed: number;
  total: number;
  created_at: string;
  started_at?: string | null;
  ended_at?: string | null;
  error?: string | null;
  statistics?: Partial<Statistics>;
  quality?: TaskResults['quality'];
  gate?: TaskResults['gate'];
  version_id?: string;
  reviewed_version_id?: string;
  logs?: Array<{ stage: string; processed?: number; total?: number; time?: string }>;
}

export interface PreprojectReviewItem {
  sample_id: string;
  status: string;
  reasons: string[];
  decision: string;
  preview?: Record<string, string>;
}

export interface PreprojectVersion {
  version_id: string;
  source_id?: string;
  parent_version_id?: string | null;
  version_type: string;
  sample_count: number;
  status: string;
  authorization_status?: string;
  revision_verification_status?: string;
  license_verification_status?: string;
  sha256?: string;
  processed_sha256?: string;
  created_at: string;
}

const base = '/preproject-data';

export const getPreprojectCatalog = () => request.get(`${base}/catalog`) as Promise<{ items: Array<{ dataset_id: string; source_url: string; license: string; revision: string }> }>;
export const importPreprojectDemo = () => request.post(`${base}/sources/demo-fixture`) as Promise<PreprojectSource>;
export const createExampleGovernanceTask = (rerun = false) => request.post(`${base}/examples/governance-task`, undefined, {params: {rerun}}) as Promise<{source: PreprojectSource; task: PreprojectTask; synthetic: boolean; resumed?: boolean}>;
export const getDefaultExample = () => request.get(`${base}/examples/default`) as Promise<{ready: boolean; source: PreprojectSource | null; task: PreprojectTask | null; template?: string}>;
export const getGovernanceTemplates = () => request.get(`${base}/templates`) as Promise<{items: Array<{id: string; name: string; description: string; rules: string[]}>}>;
export const getLocalEduChatStatus = () => request.get(`${base}/sources/local-educhat/status`) as Promise<{available: boolean; message: string}>;
export const importLocalEduChat = () => request.post(`${base}/sources/local-educhat`) as Promise<PreprojectSource & {already_registered: boolean}>;
export const startPreprojectFetch = (count: 200 | 5000) =>
  request.post(`${base}/sources/fetch`, { count }) as Promise<{ fetch_id: string; status: string; total: number }>;
export const getPreprojectFetch = (fetchId: string) =>
  request.get(`${base}/sources/fetch/${fetchId}`) as Promise<{ status: string; source_id?: string; error?: string }>;
export const listPreprojectSources = (signal?: AbortSignal) => request.get(`${base}/sources`, { signal }) as Promise<{ items: PreprojectSource[] }>;
export const listPreprojectTasks = () => request.get(`${base}/tasks`) as Promise<{ items: PreprojectTask[] }>;

export async function uploadPreprojectSource(file: File, metadata: {
  dataset_id: string;
  source_url: string;
  license: string;
  revision: string;
  split: string;
}): Promise<PreprojectSource> {
  const form = new FormData();
  form.append('file', file);
  Object.entries(metadata).forEach(([key, value]) => form.append(key, value));
  return request.post(`${base}/sources/upload`, form, { headers: { 'Content-Type': undefined } }) as Promise<PreprojectSource>;
}

export const validatePreprojectSource = (sourceId: string) =>
  request.post(`${base}/sources/${sourceId}/validate`) as Promise<{ valid: boolean; message: string }>;
export const previewPreprojectSource = (sourceId: string, offset = 0, limit = 10) =>
  request.get(`${base}/sources/${sourceId}/preview`, { params: { offset, limit } }) as Promise<{ samples: Array<Record<string, string>>; total: number }>;
export const listPreprojectVersions = (signal?: AbortSignal) => request.get(`${base}/versions`, { signal }) as Promise<{ items: PreprojectVersion[]; total: number }>;
export const comparePreprojectVersions = (left: string, right: string) => request.get(`${base}/version-comparison`, { params: { left, right } }) as Promise<VersionComparison>;
export const getPreprojectSamples = (taskId: string, offset = 0, issue = '', signal?: AbortSignal) => request.get(`${base}/tasks/${taskId}/samples`, { params: { offset, limit: 10, issue: issue || undefined }, signal }) as Promise<SamplePage>;
export const createPreprojectReleaseCandidate = (versionId: string) =>
  request.post(`${base}/versions/${encodeURIComponent(versionId)}/release-candidate`) as Promise<{ version: PreprojectVersion }>;

export const createPreprojectTask = (payload: {
  source_id: string;
  template_id?: 'education_qa' | 'general_text';
  cleaning_enabled: boolean;
  near_duplicate_enabled: boolean;
  near_duplicate_hamming_distance: number;
  near_duplicate_action: 'review_only';
  privacy_enabled: true;
  version_name: string;
}) => request.post(`${base}/tasks`, payload) as Promise<{ task: PreprojectTask; duplicate_submission: boolean }>;

export const getPreprojectTask = (taskId: string, signal?: AbortSignal) =>
  request.get(`${base}/tasks/${taskId}`, { signal }) as Promise<PreprojectTask>;
export const cancelPreprojectTask = (taskId: string) => request.post(`${base}/tasks/${taskId}/cancel`);
export const retryPreprojectTask = (taskId: string) =>
  request.post(`${base}/tasks/${taskId}/retry`) as Promise<{ task: PreprojectTask }>;
export const getPreprojectResults = (taskId: string, signal?: AbortSignal) => request.get(`${base}/tasks/${taskId}/results`, { signal }) as Promise<TaskResults>;
export const getPreprojectReport = (taskId: string, signal?: AbortSignal, _filename = 'quality_report.md') => request.get(`${base}/tasks/${taskId}/governance-report`, { signal, responseType: 'text' }) as Promise<string>;
export const getDeliveryPreview = (taskId:string, kind:'processed'|'qualified', signal?:AbortSignal) => request.get(`${base}/tasks/${taskId}/delivery-preview`, {params:{kind},signal}) as Promise<{kind:string;version_id:string;filename:string;total:number;items:Array<{sample_id:string;instruction:string;output:string;status:string;reasons:string[]}>}>;
export async function downloadGovernanceReport(taskId:string): Promise<void> {
  const blob = await request.get(`${base}/tasks/${taskId}/governance-report`, {responseType:'blob'}) as unknown as Blob;
  const url = URL.createObjectURL(blob); const anchor=document.createElement('a'); anchor.href=url; anchor.download='governance_report.md'; anchor.click(); window.setTimeout(() => URL.revokeObjectURL(url),1000);
}
export const getPreprojectReviewItems = (taskId: string, offset = 0, limit = 20, issueType?: string, signal?: AbortSignal) =>
  request.get(`${base}/tasks/${taskId}/review-items`, { params: { offset, limit, issue_type: issueType || undefined }, signal }) as Promise<{ items: PreprojectReviewItem[]; total: number; pending_count: number; revision: number; rebuild_status?: string }>;
export const getPreprojectReviewHistory = (taskId: string, signal?: AbortSignal) =>
  request.get(`${base}/tasks/${taskId}/reviews`, { signal }) as Promise<{ items: Array<{ sample_id: string; decision: string; reviewed_at: string }>; total: number }>;
export const submitPreprojectReview = (taskId: string, payload: {
  sample_id: string;
  decision: 'accept' | 'edit' | 'quarantine' | 'reject';
  issue_type?: string;
  edited_content?: Record<string, string>;
  notes?: string;
  expected_revision: number;
}) => request.post(`${base}/tasks/${taskId}/reviews`, payload) as Promise<{ quality_recomputed: boolean; revision: number }>;
export const rebuildPreprojectReview = (taskId: string) => request.post(`${base}/tasks/${taskId}/reviews/rebuild`) as Promise<{ quality_recomputed: boolean }>;

export async function downloadPreprojectFile(taskId: string, filename: string): Promise<void> {
  const blob = await request.get(`${base}/tasks/${taskId}/files/${encodeURIComponent(filename)}`, {
    responseType: 'blob',
  }) as Blob;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
