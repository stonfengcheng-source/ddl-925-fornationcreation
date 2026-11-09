export interface Metric {
  value: unknown; numerator: number | null; denominator: number | null;
  formula?: string; definition?: string; scope?: string; not_measurable_reason?: string | null;
  issue_sample_ids?: string[];
}
export interface Stage { stage: string; status: string; input_count: number; output_count: number; processed_count: number; error_count: number; duration_seconds: number; rules: unknown; }
export interface Statistics {
  input_nonblank_lines: number; raw_sample_count: number; final_retained_count: number;
  status_counts: Record<string, number>; stages?: Stage[]; exact_duplicate_count: number;
  normalized_duplicate_count: number; near_duplicate_sample_count: number; privacy_hit_count: number;
  review_count: number; quarantine_count: number; drop_count: number;
  automatic_repair_count?: number; cleaning_modified_count?: number; privacy_residual_count?: number;
  action_counts?: Record<string, number | string | null>;
}
export interface TaskResults {
  statistics: Statistics; quality: { metrics: Record<string, Record<string, Metric>> };
  gate: { decision: string; release_eligible: boolean; reasons: string[] };
  files: string[]; review_samples: Array<{ sample_id?: string; status: string; reasons?: string[] }>;
  reviewed_version_id?: string | null;
  issue_counts?: Record<string, number>;
  outcome?: {actions:Record<string, number|string|null>; engineering:{status:string;candidate_count:number;summary:string;scope:string;pending_review:number}; professional:{status:string;summary:string;manual_reviewed:number;pending_review:number}; publication:{status:string;release_eligible:boolean;reasons:string[];revision_verified:boolean;license_verified:boolean;redistribution_authorized:boolean}};
}
export interface Sample { sample_id: string; source_record_id: string; status: string; reasons: string[]; before: Record<string, string> | null; after: Record<string, string>; cleaning_changes: string[]; duplicate_type?: string; source_mapping?:Record<string,string>; changed_fields?:string[]; change_kind?:string; review_decision?:string; review_recheck?:string; }
export interface SamplePage { items: Sample[]; total: number; }
export interface VersionComparison { added_count: number; removed_count: number; changed_count: number | null; status_changed_count: number | null; reason: string | null; qualified_change?: { left: number | null; right: number | null }; metrics?: Array<{ dimension: string; metric: string; left: unknown; right: unknown; reason?: string }>; metrics_reason?: string | null; authorization?: { left: string; right: string }; source_verification?: Array<{ revision: string | null; license: string | null }>; }
