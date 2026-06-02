export interface Task {
  id: number;
  user_task_no: number;
  task_type: "SAST" | "DAST" | "SCA";
  scanner_engine?: "bandit" | "semgrep" | null;
  task_name?: string | null;
  description?: string | null;
  status: "PENDING" | "RUNNING" | "SUCCESS" | "FAILED" | "TIMEOUT" | "CANCELLED";
  progress: number;
  result_summary?: string | null;
  target_name?: string | null;
  target_url?: string | null;
  timeout_seconds?: number | null;
  authorization_confirmed?: boolean;
  target_host?: string | null;
  target_ip?: string | null;
  target_policy?: string | null;
  error_message?: string | null;
  duration_ms?: number | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
}
