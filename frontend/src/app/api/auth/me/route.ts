// Current user: forwards the cookie token to FastAPI's GET /auth/me.
// The client uses this to hydrate the signed-in user and to detect an
// expired/invalid token (401 → clear cookie → back to /login).

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { backendUrl, TOKEN_COOKIE } from "@/lib/server/backend";

export async function GET() {
  const cookieStore = await cookies();
  const token = cookieStore.get(TOKEN_COOKIE)?.value;
  if (!token) {
    return NextResponse.json(
      { error: true, type: "http_error", status_code: 401, detail: "Not signed in" },
      { status: 401 },
    );
  }

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl("/auth/me"), {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    return NextResponse.json(
      { error: true, type: "proxy_error", detail: "Backend is unreachable. Is the API running?" },
      { status: 502 },
    );
  }

  const data = await upstream.json().catch(() => null);
  if (upstream.status === 401) {
    cookieStore.delete(TOKEN_COOKIE);
  }
  return NextResponse.json(data ?? { error: true, detail: "Request failed" }, {
    status: upstream.status,
  });
}
