// Browser-side API client. Every call goes to the Next.js proxy
// (/api/backend/*) or an auth route handler (/api/auth/*) — never directly
// to FastAPI — so the JWT stays in its httpOnly cookie (decisions.md §11.5).

import type {
  DashboardData,
  ItemStatus,
  Job,
  Match,
  MatchListItem,
  ModelList,
  Resume,
  User,
} from "./types";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let detail = `Request failed (${response.status})`;
  try {
    const body = await response.json();
    if (body?.detail) detail = body.detail;
    else if (body?.message) detail = body.message;
    if (body?.details?.length) {
      detail = body.details.map((d: { message: string }) => d.message).join(", ");
    }
  } catch {
    // Non-JSON error body — keep the generic message.
  }
  // The backend's match rate limit (10/min, Phase 6) deserves a calmer label.
  if (response.status === 429) {
    detail = "You're doing that a bit fast — wait a few seconds and try again.";
  }
  return new ApiError(response.status, detail);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/backend${path}`, init);
  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function jsonInit(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  };
}

export const api = {
  // ── Auth (route handlers, not the generic proxy) ──
  async login(email: string, password: string): Promise<void> {
    const response = await fetch("/api/auth/login", jsonInit("POST", { email, password }));
    if (!response.ok) throw await parseError(response);
  },
  async register(email: string, password: string): Promise<User> {
    const response = await fetch(
      "/api/auth/register",
      jsonInit("POST", { email, password }),
    );
    if (!response.ok) throw await parseError(response);
    return (await response.json()) as User;
  },
  async logout(): Promise<void> {
    await fetch("/api/auth/logout", { method: "POST" });
  },
  async me(): Promise<User> {
    const response = await fetch("/api/auth/me");
    if (!response.ok) throw await parseError(response);
    return (await response.json()) as User;
  },

  // ── Resumes ──
  listResumes: () => request<Resume[]>("/resumes"),
  getResume: (id: number) => request<Resume>(`/resumes/${id}`),
  resumeStatus: (id: number) => request<ItemStatus>(`/resumes/${id}/status`),
  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Resume>("/resumes", { method: "POST", body: form });
  },
  reprocessResume: (id: number) =>
    request<ItemStatus>(`/resumes/${id}/reprocess`, { method: "POST" }),

  // ── Jobs ──
  listJobs: () => request<Job[]>("/jobs"),
  getJob: (id: number) => request<Job>(`/jobs/${id}`),
  jobStatus: (id: number) => request<ItemStatus>(`/jobs/${id}/status`),
  createJob: (raw_text: string, title?: string, company?: string) =>
    request<Job>("/jobs", jsonInit("POST", { raw_text, title, company })),

  // ── Matching ──
  runMatch: (resumeId: number, jobId: number, generateFeedback: boolean) =>
    request<Match>(
      `/match/${resumeId}/${jobId}?generate_feedback=${generateFeedback}`,
      { method: "POST" },
    ),
  listMatches: (params?: { resume_id?: number; job_id?: number }) => {
    const query = new URLSearchParams();
    if (params?.resume_id) query.set("resume_id", String(params.resume_id));
    if (params?.job_id) query.set("job_id", String(params.job_id));
    const suffix = query.toString() ? `?${query}` : "";
    return request<MatchListItem[]>(`/matches${suffix}`);
  },
  getMatch: (id: number) => request<Match>(`/matches/${id}`),
  regenerateFeedback: (matchId: number, model?: string) =>
    request<{ match_id: number; ai_feedback: string; model_used: string }>(
      `/matches/${matchId}/feedback`,
      jsonInit("POST", model ? { model } : {}),
    ),
  matchPdfUrl: (matchId: number) => `/api/backend/matches/${matchId}/export-pdf`,

  // ── AI ──
  listModels: () => request<ModelList>("/ai/models"),
  rewriteBullet: (bullet: string, targetJob?: string, missingSkills?: string[]) =>
    request<{ original_bullet: string; rewrite_content: string; model_used: string }>(
      "/ai/rewrite-bullet",
      jsonInit("POST", {
        bullet,
        target_job: targetJob,
        missing_skills: missingSkills,
      }),
    ),

  // ── Analytics ──
  dashboard: () => request<DashboardData>("/analytics/dashboard"),
};

/**
 * Stream AI feedback for a match, token by token.
 * The backend speaks SSE: lines of `data: {"token": "..."}` then `data: [DONE]`.
 */
export async function streamMatchFeedback(
  matchId: number,
  onToken: (token: string) => void,
  model?: string,
): Promise<string> {
  const query = model ? `?model=${encodeURIComponent(model)}` : "";
  const response = await fetch(
    `/api/backend/matches/${matchId}/feedback/stream${query}`,
  );
  if (!response.ok || !response.body) throw await parseError(response);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let full = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const payload = trimmed.slice("data:".length).trim();
      if (payload === "[DONE]") return full;
      try {
        const parsed = JSON.parse(payload) as { token?: string };
        if (parsed.token) {
          full += parsed.token;
          onToken(parsed.token);
        }
      } catch {
        // Partial JSON across chunks — the next read completes it.
      }
    }
  }
  return full;
}
