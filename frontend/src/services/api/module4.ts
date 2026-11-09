import request from '../request';

export type Module4Action =
  | 'check_training_env' | 'check_eval_env' | 'fix_eval_dependencies'
  | 'build_data' | 'validate_data' | 'prepare_configs' | 'train' | 'merge'
  | 'make_eval_manifest' | 'eval_dry' | 'eval_run' | 'eval_score' | 'compare_results' | 'export_badcases';

export interface Module4Config {
  confirm_install?: boolean;
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
  data_version_id: string;
  candidate_config_id: string;
}

export interface CandidateVersion { version_id: string; dataset_id?: string; sample_count: number; release_eligible: boolean; authorization_status: string; license_verification_status: string; revision_verification_status: string; }
export interface PreflightCheck { key: string; ready: boolean; message: string }
export interface Module4Preflight { evaluation: { ready: boolean; checks: PreflightCheck[]; dry_run_ready: boolean; score_ready: boolean }; training: { ready: boolean; checks: PreflightCheck[] }; base_model: { ready: boolean; message: string }; training_environment?: Module4Status['training_environment'] }

export interface Module4Status {
  available_variants?: string[];
  available_models?: string[];
  pending_variants?: Record<string, string>;
  training_environment?: {
    checked: boolean;
    checked_at?: number;
    python_version?: string | null;
    interpreter_matches?: boolean;
    training_ready?: boolean;
    missing_packages?: string[];
    package_versions?: Record<string, string | null>;
    training_cli_available?: boolean;
    cuda_available?: boolean;
    cuda_state?: string;
    driver_detected?: boolean;
    torch_cuda_version?: string | null;
    interpreter_exists?: boolean;
    gpus?: string[];
    message?: string;
  } | null;
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
export const getCandidateVersions = (): Promise<{items: CandidateVersion[]}> => request.get('/module4/candidate-versions');
export const prepareCandidateConfig = (config: Module4Config): Promise<{config_id: string; version_id: string; sample_count: number; message: string}> => request.post('/module4/prepare-candidate-config', {version_id: config.data_version_id, base_model: config.base_model, template: config.template, epochs: config.epochs, precision: config.precision, seed: config.seed});
export const getModule4Preflight = (config: Module4Config, signal?: AbortSignal): Promise<Module4Preflight> => request.post('/module4/preflight', {action:'inspect', config}, {signal});
