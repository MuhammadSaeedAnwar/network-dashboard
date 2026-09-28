export interface Host {
  id: number;
  name: string;
  address: string;
  description: string | null;
  authorized: boolean;
  expected_ports: number[] | null;
  expected_http_url: string | null;
  latency_warning_ms: number | null;
  created_at: string;
}

export interface HostSummary extends Host {
  latest_status: "ok" | "warning" | "critical" | "unknown";
  latest_latency_ms: number | null;
  open_port_count: number | null;
  open_alert_count: number;
  last_checked_at: string | null;
}

export interface HealthCheckResult {
  id: number;
  host_id: number;
  check_type: string;
  target: string;
  success: boolean;
  status: "ok" | "warning" | "critical" | "unknown";
  detail: string;
  latency_ms: number | null;
  checked_at: string;
}

export interface RunChecksResponse {
  host_id: number;
  results: HealthCheckResult[];
  alerts_raised: number;
}

export interface PortResult {
  id: number;
  port_number: number;
  protocol: string;
  state: string;
  service_name: string | null;
  service_product: string | null;
  service_version: string | null;
}

export interface Scan {
  id: number;
  host_id: number;
  target: string;
  status: "running" | "completed" | "failed";
  top_ports: number;
  error_detail: string | null;
  started_at: string;
  completed_at: string | null;
  ports: PortResult[];
}

export interface Alert {
  id: number;
  host_id: number;
  source: "health_check" | "scan";
  severity: "warning" | "critical";
  message: string;
  resolved: boolean;
  raised_at: string;
}

export interface DashboardSummary {
  total_hosts: number;
  hosts_ok: number;
  hosts_warning: number;
  hosts_critical: number;
  hosts_unknown: number;
  open_alerts: number;
  total_scans: number;
}

export interface NewHostInput {
  name: string;
  address: string;
  description?: string;
  expected_ports?: number[];
  expected_http_url?: string;
  latency_warning_ms?: number;
  authorized_confirmation: boolean;
}
