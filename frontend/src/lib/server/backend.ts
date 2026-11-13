// Server-side helpers for talking to the FastAPI backend.
// Used only by route handlers (app/api/*) — never imported by client code,
// so API_INTERNAL_URL and the JWT cookie value stay off the browser.

export const API_INTERNAL_URL =
  process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export const TOKEN_COOKIE = "access_token";

/** Lifetime mirrors the backend JWT (ACCESS_TOKEN_EXPIRE_MINUTES=1440 → 24h). */
export const TOKEN_COOKIE_MAX_AGE = 60 * 60 * 24;

export function backendUrl(path: string): string {
  return `${API_INTERNAL_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
