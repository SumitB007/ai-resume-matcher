// Generic authenticated proxy to the FastAPI backend.
//
// Why this exists (decisions.md §11.5): the JWT lives in an httpOnly cookie,
// so browser JavaScript can never read it — every app API call goes through
// here, and this handler attaches `Authorization: Bearer <token>` server-side.
// It forwards JSON, multipart uploads, SSE streams and PDF downloads without
// buffering response bodies, and passes the backend's error envelope through
// untouched so the client sees one consistent error shape.

import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { backendUrl, TOKEN_COOKIE } from "@/lib/server/backend";

async function proxy(request: NextRequest, path: string[]) {
  const cookieStore = await cookies();
  const token = cookieStore.get(TOKEN_COOKIE)?.value;
  if (!token) {
    return NextResponse.json(
      { error: true, type: "http_error", status_code: 401, detail: "Not signed in" },
      { status: 401 },
    );
  }

  const target = backendUrl(`/${path.join("/")}`) + request.nextUrl.search;

  const headers = new Headers();
  headers.set("Authorization", `Bearer ${token}`);
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);

  const init: RequestInit = { method: request.method, headers };
  if (request.method !== "GET" && request.method !== "HEAD") {
    // arrayBuffer (not a stream) so multipart uploads forward byte-exact.
    init.body = await request.arrayBuffer();
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, init);
  } catch {
    return NextResponse.json(
      {
        error: true,
        type: "proxy_error",
        status_code: 502,
        detail: "Backend is unreachable. Is the API running?",
      },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers();
  for (const name of ["content-type", "content-disposition", "x-total-count"]) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }

  // upstream.body is a stream — returning it directly keeps SSE feedback
  // streaming and PDF downloads unbuffered.
  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}
