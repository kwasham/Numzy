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
	if (sessionId) {
		try {
			// Prefer SDK when available
			if (clerkClient?.sessions?.revokeSession) {
				await clerkClient.sessions.revokeSession(sessionId);
			} else if (process.env.CLERK_SECRET_KEY) {
				// REST fallback
				const api = process.env.CLERK_API_URL || "https://api.clerk.com/v1";
				await fetch(`${api}/sessions/${sessionId}/revoke`, {
					method: "POST",
					headers: { Authorization: `Bearer ${process.env.CLERK_SECRET_KEY}` },
					cache: "no-store",
				});
			}
		} catch (error) {
			console.error("[clerk] revokeSession failed", error);
		}
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
