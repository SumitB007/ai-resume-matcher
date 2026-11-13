// Register: plain pass-through to FastAPI. The backend's register endpoint
// returns the created user (no token), so the client chains into /api/auth/login
// immediately after a successful signup.

import { NextRequest, NextResponse } from "next/server";

import { backendUrl } from "@/lib/server/backend";

export async function POST(request: NextRequest) {
  const body = await request.text();

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl("/auth/register"), {
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
  return NextResponse.json(data ?? { error: true, detail: "Registration failed" }, {
    status: upstream.status,
  });
}
