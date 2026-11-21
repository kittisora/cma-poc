import type { Analysis, AreaOption, Branding, CMARequest, Meta, ReportModel, SearchResult } from "@/lib/types";

const qs = (params: Record<string, string | null | undefined>) =>
  Object.entries(params)
    .filter(([, v]) => v)
    .map(([k, v]) => `${k}=${encodeURIComponent(v as string)}`)
    .join("&");

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const body = await res.json();
      msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

export const api = {
  meta: () => request<Meta>("/api/meta"),
  search: (q: string, zip: string, signal?: AbortSignal) =>
    request<{ results: SearchResult[]; timing_ms: number }>(
      `/api/search?q=${encodeURIComponent(q)}${zip ? `&zip=${zip}` : ""}`,
      { signal },
    ),
  areas: (f: { subdivision?: string | null; block?: string | null }, signal?: AbortSignal) =>
    request<{ subdivisions: AreaOption[]; blocks: AreaOption[]; streets: AreaOption[] }>(`/api/search/areas?${qs(f)}`, { signal }),
  properties: (f: { subdivision?: string | null; block?: string | null; street?: string | null }, signal?: AbortSignal) =>
    request<{ results: SearchResult[]; total: number; timing_ms: number }>(`/api/search/properties?${qs(f)}`, { signal }),
  analyze: (req: CMARequest, signal?: AbortSignal) =>
    request<Analysis>("/api/cma/analyze", { method: "POST", body: JSON.stringify(req), signal }),
  setInput: (pin: string, field: string, value: number | string | null, note?: string) =>
    request(`/api/properties/${encodeURIComponent(pin)}/inputs`, {
      method: "PUT",
      body: JSON.stringify({ field, value, note }),
    }),
  regression: (params: Record<string, string | number | undefined>) => {
    const q = Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== "")
      .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
      .join("&");
    return request<Record<string, any>>(`/api/workbook/regression?${q}`);
  },
  getWorkbookSubject: () => request<{ kind: "workbook" | "property"; key: string; label?: string }>("/api/workbook/subject"),
  putWorkbookSubject: (kind: "workbook" | "property", key: string) =>
    request<{ kind: "workbook" | "property"; key: string; label: string }>("/api/workbook/subject", {
      method: "PUT",
      body: JSON.stringify({ kind, key }),
    }),
  getBranding: () => request<Branding>("/api/settings/branding"),
  putBranding: (b: Branding) => request<Branding>("/api/settings/branding", { method: "PUT", body: JSON.stringify(b) }),
  narrative: (req: CMARequest) =>
    request<{ narrative: string; generated_by: string; note?: string; model?: string }>("/api/agent/narrative", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  chat: (cma: CMARequest, messages: { role: string; content: string }[]) =>
    request<{ reply: string; tool_calls: { tool: string; input: Record<string, unknown>; error: boolean }[] }>(
      "/api/agent/chat",
      { method: "POST", body: JSON.stringify({ cma, messages }) },
    ),
  preview: (body: unknown) => request<ReportModel>("/api/reports/preview", { method: "POST", body: JSON.stringify(body) }),
};

/** POST the reviewed CMA and save the returned PDF/XLSX. */
export async function downloadReport(format: "pdf" | "xlsx", body: unknown): Promise<string> {
  const res = await fetch(`/api/reports/${format}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      msg = (await res.json()).detail ?? msg;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, msg);
  }
  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition") ?? "";
  const name = /filename="([^"]+)"/.exec(cd)?.[1] ?? `CMA.${format}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
  return name;
}
