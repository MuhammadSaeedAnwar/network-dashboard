import type {
  Alert,
  DashboardSummary,
  Host,
  HostSummary,
  NewHostInput,
  RunChecksResponse,
  Scan,
} from "./types";

// Base URL comes from an env var at build time -- never hardcoded, so the
// same build can point at different backends via VITE_API_BASE_URL.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!resp.ok) {
    let detail: unknown;
    try {
      detail = await resp.json();
    } catch {
      detail = resp.statusText;
    }
    throw new ApiError(resp.status, detail);
  }

  if (resp.status === 204) {
    return undefined as T;
  }
  return (await resp.json()) as T;
}

export const api = {
  listHosts: () => request<HostSummary[]>("/api/hosts"),
  getHost: (id: number) => request<Host>(`/api/hosts/${id}`),
  createHost: (payload: NewHostInput) =>
    request<Host>("/api/hosts", { method: "POST", body: JSON.stringify(payload) }),
  deleteHost: (id: number) => request<void>(`/api/hosts/${id}`, { method: "DELETE" }),

  runChecks: (hostId: number) =>
    request<RunChecksResponse>(`/api/hosts/${hostId}/checks/run`, { method: "POST" }),
  listChecks: (hostId: number) => request<RunChecksResponse["results"]>(`/api/hosts/${hostId}/checks`),

  createScan: (hostId: number, topPorts: number | undefined, authorizationAck: boolean) =>
    request<Scan>(`/api/hosts/${hostId}/scans`, {
      method: "POST",
      body: JSON.stringify({ top_ports: topPorts, authorization_ack: authorizationAck }),
    }),
  listScans: (hostId: number) => request<Scan[]>(`/api/hosts/${hostId}/scans`),

  listAlerts: (params: { hostId?: number; resolved?: boolean } = {}) => {
    const qs = new URLSearchParams();
    if (params.hostId !== undefined) qs.set("host_id", String(params.hostId));
    if (params.resolved !== undefined) qs.set("resolved", String(params.resolved));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<Alert[]>(`/api/alerts${suffix}`);
  },
  resolveAlert: (id: number) => request<Alert>(`/api/alerts/${id}/resolve`, { method: "POST" }),

  dashboardSummary: () => request<DashboardSummary>("/api/dashboard/summary"),
};
