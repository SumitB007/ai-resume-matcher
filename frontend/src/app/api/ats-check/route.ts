// Public proxy for the anonymous ATS checker.
//
// Unlike /api/backend/*, this handler requires NO session cookie — it exists
// for the public /resume-checker page. It forwards the multipart upload to
// FastAPI's POST /ats/check-upload, which parses and checks in-memory and
// persists nothing. This is the only unauthenticated proxy route, and it can
// reach exactly one backend endpoint.

import { NextRequest, NextResponse } from "next/server";

import { backendUrl } from "@/lib/server/backend";

export async function POST(request: NextRequest) {
  const contentType = request.headers.get("content-type");
  const headers = new Headers();
  if (contentType) headers.set("content-type", contentType);

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl("/ats/check-upload"), {
      method: "POST",
      headers,
      body: await request.arrayBuffer(),
    });
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
  const upstreamType = upstream.headers.get("content-type");
  if (upstreamType) responseHeaders.set("content-type", upstreamType);

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}
