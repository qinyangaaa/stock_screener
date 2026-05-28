export interface Recommendation {
  id: number;
  rank: number;
  code: string;
  name: string;
  score: number;
  signal: "strong_buy" | "buy" | "watch";
  change_pct: number;
  volume_ratio: number;
  turnover: number;
  market_cap: number;
  rule_details: Record<string, { passed: boolean; detail: string }>;
  screening_date: string;
  created_at: string;
}

export interface RunStatus {
  id: number;
  task_id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  total_stocks: number;
  passed_stage1: number;
  passed_all: number;
  error: string | null;
}

export interface LatestResponse {
  date: string | null;
  total: number;
  recommendations: Recommendation[];
  last_run: RunStatus | null;
  is_trading_day: boolean;
}

export interface HistoryResponse {
  date: string;
  total: number;
  recommendations: Recommendation[];
}

export interface TaskStatus {
  task_id: string;
  progress: {
    stage: string;
    msg: string;
    percent: number;
  };
  run_info: RunStatus | null;
}

export interface StockDetailResponse {
  code: string;
  history: Recommendation[];
  last_run: RunStatus | null;
}

// 筛选明细相关类型
export interface Stage1FailedSample {
  code: string;
  name: string;
  change_pct?: number;
  volume_ratio?: number;
  turnover?: number;
  market_cap?: number;
  detail: string;
}

export interface Stage1Detail {
  passed: number;
  rule_fails: Record<string, number>;
  failed_samples: Record<string, Stage1FailedSample[]>;
  is_extreme: boolean;
}

export interface Stage2CandidateResult {
  code: string;
  name: string;
  change_pct: number;
  volume_ratio: number;
  turnover: number;
  market_cap: number;
  rule_results: Record<string, { passed: boolean; detail: string }>;
}

export interface Stage2FailedResult extends Stage2CandidateResult {
  failed_rule: string;
}

export interface Stage2Detail {
  passed: number;
  rule_fails: Record<string, number>;
  candidates: Stage2CandidateResult[];
  failed: Stage2FailedResult[];
}

export interface ScreeningDetails {
  total_stocks: number;
  stage1: Stage1Detail;
  stage2: Stage2Detail;
}

export interface ScreeningDetailsResponse {
  task_id?: string;
  details: ScreeningDetails;
}
