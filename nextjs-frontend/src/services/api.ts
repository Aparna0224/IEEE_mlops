import type {
  GenerateRequest,
  GenerateResponse,
  TaskStatus,
  HealthResponse,
  FullValidationResponse,
  ReviewReport,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

/* ── Health ── */
export const checkHealth = () => request<HealthResponse>("/api/langgraph/health");

/* ── Generate ── */
export const generatePaper = (body: GenerateRequest) =>
  request<GenerateResponse>("/api/langgraph/generate", {
    method: "POST",
    body: JSON.stringify(body),
  });

/* ── Status polling ── */
export const getTaskStatus = (taskId: string) =>
  request<TaskStatus>(`/api/langgraph/status/${taskId}`);

/* ── Validation metrics ── */
export const getValidation = (taskId: string) =>
  request<FullValidationResponse>(`/api/langgraph/validation/${taskId}`);

/* ── Download PDF (returns blob URL) ── */
export async function downloadPdf(taskId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/langgraph/download/${taskId}`);
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

/* ── IEEE LaTeX PDF export ── */
export async function downloadIeeePdf(taskId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/langgraph/download/${taskId}`, {
    method: "GET",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "IEEE PDF export failed");
  }
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

/* ── IEEE LaTeX source export ── */
export async function downloadIeeeLatex(taskId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/langgraph/latex/${taskId}`, {
    method: "GET",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "LaTeX export failed");
  }
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

/* ── Tasks list ── */
export const listTasks = () =>
  request<{ tasks: TaskStatus[]; total: number }>("/api/langgraph/tasks");

/* ── Delete task ── */
export const deleteTask = (taskId: string) =>
  request<{ message: string }>(`/api/langgraph/tasks/${taskId}`, { method: "DELETE" });

/* ── Download DOCX ── */
export const downloadDocx = async (taskId: string): Promise<Blob> => {
  const response = await fetch(`${API_BASE}/api/langgraph/export/docx/${taskId}`);
  if (!response.ok) throw new Error("DOCX download failed");
  return response.blob();
};

/* ── Review report ── */
export const getReviewReport = (taskId: string): Promise<ReviewReport> =>
  request<ReviewReport>(`/api/langgraph/review/${taskId}`);
