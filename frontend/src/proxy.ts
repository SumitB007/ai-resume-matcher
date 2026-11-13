// Optimistic auth gate (Next.js 16 Proxy — formerly Middleware).
//
// Per the framework's own guidance this is ONLY an optimistic check: it reads
// the session cookie's presence, never validates it. Real validation happens
// on every API call (the proxy route returns 401 and /api/auth/me clears a
// dead cookie). Keeping this dumb keeps it fast on every navigation.

import { NextRequest, NextResponse } from "next/server";

import { TOKEN_COOKIE } from "@/lib/server/backend";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasToken = Boolean(request.cookies.get(TOKEN_COOKIE)?.value);

  if (pathname.startsWith("/app") && !hasToken) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if ((pathname === "/login" || pathname === "/signup") && hasToken) {
    return NextResponse.redirect(new URL("/app", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/app/:path*", "/login", "/signup"],
};
