import { NextResponse } from "next/server";
import { auth, clerkClient } from "@clerk/nextjs/server";

import { getAppUrl } from "@/lib/get-app-url";

// To align with the other auth providers, we've created a sign-out route.
// This can done also from the client side using the `useClerk()` hook.
// For more information, see: https://clerk.com/docs/references/react/use-clerk

// This example is nice to have if you're looking for a solution to sign out the user from the server side for some reason.

export async function GET() {
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
