import { NextResponse } from "next/server";
import { auth, clerkClient } from "@clerk/nextjs/server";

import { getAppUrl } from "@/lib/get-app-url";

// Hardened sign‑out route for Clerk.
//
// This route only allows POST requests to mitigate logout‑CSRF.  It verifies
// that the request originates from the same origin as the application by
// checking the `Origin` or `Referer` header.  If the origin is not trusted
// the request is rejected with a 403.  On successful sign‑out the current
// session is revoked, the session cookie is cleared and the client is
// redirected to the application root.  See docs/clerk-auth.md for details.

export async function POST(request) {
  // Check origin/referer for CSRF protection
  const originHeader = request.headers.get("origin") || request.headers.get("referer") || "";
  const appUrl = new URL(getAppUrl());
  if (originHeader && !originHeader.startsWith(appUrl.origin)) {
    return new NextResponse("Forbidden", { status: 403 });
  }
  const { sessionId } = await auth();
  const client = await clerkClient();
  if (sessionId) {
    await client.sessions.revokeSession(sessionId);
  }
  const res = new NextResponse(undefined, { status: 307 });
  // Cleanup the session cookie
  res.cookies.delete("__session");
  res.headers.set("Location", getAppUrl().toString());
  return res;
}

export function GET() {
  return new NextResponse("Method Not Allowed", { status: 405 });
}