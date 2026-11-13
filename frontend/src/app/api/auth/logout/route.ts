// Logout: the JWT is stateless, so "logging out" is deleting the cookie.
// (The token itself remains valid until expiry — a known JWT trade-off the
// backend accepted in Phase 2, decisions.md §2.2.)

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { TOKEN_COOKIE } from "@/lib/server/backend";

export async function POST() {
  const cookieStore = await cookies();
  cookieStore.delete(TOKEN_COOKIE);
  return NextResponse.json({ ok: true });
}
