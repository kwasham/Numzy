import "server-only";

import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isProtectedRoute = createRouteMatcher(["/dashboard(.*)"]);

export const middleware = clerkMiddleware(async (auth, req) => {
	if (isProtectedRoute(req)) await auth.protect();
});
