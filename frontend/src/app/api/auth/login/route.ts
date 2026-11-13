// Login: forwards credentials to FastAPI and stores the returned JWT in an
// httpOnly cookie. The token is never returned to browser JavaScript.

import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import {
  backendUrl,
  TOKEN_COOKIE,
  TOKEN_COOKIE_MAX_AGE,
} from "@/lib/server/backend";

export async function POST(request: NextRequest) {
  const body = await request.text();

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl("/auth/login"), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
    });
  } catch {
    return NextResponse.json(
      { error: true, type: "proxy_error", detail: "Backend is unreachable. Is the API running?" },
      { status: 502 },
    );
  }

  const data = await upstream.json().catch(() => null);
  if (!upstream.ok || !data?.access_token) {
    return NextResponse.json(
      data ?? { error: true, type: "http_error", detail: "Login failed" },
      { status: upstream.status },
    );
  }

  const cookieStore = await cookies();
  cookieStore.set(TOKEN_COOKIE, data.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: TOKEN_COOKIE_MAX_AGE,
  });

  return NextResponse.json({ ok: true });
}
