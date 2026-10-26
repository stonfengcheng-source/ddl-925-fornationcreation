import request from '../request';

export type Module4Action =
  | 'check_training_env' | 'check_eval_env' | 'fix_eval_dependencies'
  | 'build_data' | 'validate_data' | 'prepare_configs' | 'train' | 'merge'
  | 'make_eval_manifest' | 'eval_dry' | 'eval_run' | 'eval_score' | 'compare_results' | 'export_badcases';

export interface Module4Config {
  training_python: string;
  predictions_path: string;
  badcase_model: string;
  raw_path: string;
  evaluated_path: string;
  datajuicer_path: string;
  sample_count: number;
  seed: number;
  base_model: string;
  template: string;
  epochs: number;
  precision: 'bf16' | 'fp16';
  variant: string;
  opencompass_env: string;
  eval_workspace: string;
  eval_mode: 'smoke' | 'quick' | 'light' | 'standard' | 'extended' | 'thorough' | 'full' | 'custom';
  eval_subjects: string[];
  eval_samples_per_subject: number;
  eval_all_questions: boolean;
  eval_batch_size: number;
  eval_max_out_len: number;
  eval_model: string;
}

export interface Module4Status {
  available_variants?: string[];
  available_models?: string[];
  pending_variants?: Record<string, string>;
  task: {
    status: 'idle' | 'running' | 'stopping' | 'success' | 'failed' | 'stopped';
    label: string;
    exit_code: number | null;
    started_at: number | null;
    finished_at: number | null;
    logs: string;
  };
  artifacts: Record<string, boolean | Record<string, boolean>>;
  progress?: Record<string, boolean | Record<string, boolean>>;
  progress_parameters?: Record<string, Partial<Module4Config>>;
}

export interface ResultRow {
  model: string;
  benchmark: string;
  metric: string;
  runs: string;
  mean_score: string;
  std_score: string;
  base_mean_score: string;
  delta_score: string;
}

export const getModule4Status = (signal?: AbortSignal): Promise<Module4Status> =>
  request.get('/module4/status', { signal });
export const runModule4 = (action: Module4Action, config: Module4Config): Promise<{ message: string }> =>
  request.post('/module4/run', { action, config });
export const stopModule4 = (): Promise<{ message: string }> => request.post('/module4/stop');
export const clearModule4Logs = (): Promise<{ ok: boolean }> => request.post('/module4/clear');
export const getModule4Results = (): Promise<{ rows: ResultRow[]; metadata?: { sample_count?: number } }> => request.get('/module4/results');
