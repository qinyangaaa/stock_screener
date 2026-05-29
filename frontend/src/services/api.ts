import type { LatestResponse, HistoryResponse, TaskStatus, StockDetailResponse, ScreeningDetailsResponse, ConfigResponse, ScreeningRunsResponse } from "../types/stock";

const BASE = "";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function fetchLatest(): Promise<LatestResponse> {
  return request<LatestResponse>("/api/recommendations/latest");
}

export function fetchHistory(date: string): Promise<HistoryResponse> {
  return request<HistoryResponse>(`/api/recommendations/history?date=${date}`);
}

export function fetchHistoryDates(): Promise<{ dates: string[] }> {
  return request("/api/recommendations/history/dates");
}

export function triggerScreening(): Promise<{ task_id?: string; status?: string; warning?: string; error?: string }> {
  return request("/api/screen/run", { method: "POST" });
}

export function cancelScreening(): Promise<{ status: string }> {
  return request("/api/screen/cancel", { method: "POST" });
}

export function fetchTaskStatus(taskId: string): Promise<TaskStatus> {
  return request<TaskStatus>(`/api/screen/status/${taskId}`);
}

export function fetchStockDetail(code: string): Promise<StockDetailResponse> {
  return request<StockDetailResponse>(`/api/stock/${code}/detail`);
}

export function fetchScreeningDetails(taskId?: string): Promise<ScreeningDetailsResponse> {
  const url = taskId ? `/api/screen/details/${taskId}` : "/api/screen/details";
  return request<ScreeningDetailsResponse>(url);
}

export function fetchConfig(): Promise<ConfigResponse> {
  return request<ConfigResponse>("/api/config");
}

export function updateConfig(key: string, value: string | number | boolean): Promise<{ status: string }> {
  return request("/api/config", {
    method: "PUT",
    body: JSON.stringify({ key, value }),
  });
}

export function updateConfigBatch(items: Record<string, string | number | boolean>): Promise<{ status: string }> {
  return request("/api/config", {
    method: "PUT",
    body: JSON.stringify({ action: "batch", items }),
  });
}

export function resetConfig(): Promise<{ status: string }> {
  return request("/api/config", {
    method: "PUT",
    body: JSON.stringify({ action: "reset" }),
  });
}

export function fetchScreeningRuns(): Promise<ScreeningRunsResponse> {
  return request<ScreeningRunsResponse>("/api/screen/runs");
}

export function fetchHealth(): Promise<{ status: string; date: string }> {
  return request("/api/health");
}
