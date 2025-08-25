import "server-only";

import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

// Define routes that require authentication.  In addition to the dashboard,
// protect any billing and subscription pages and API routes served via the
// Next.js app.  Adjust this list as your application grows.
const isProtectedRoute = createRouteMatcher([
  "/dashboard(.*)",
  "/billing(.*)",
  "/subscribe(.*)",
  "/api/(.*)",
]);

export const middleware = clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req)) {
    await auth.protect();
  }
});

// Optional: configure the matcher to exclude static assets from middleware
export const config = {
  matcher: ["/(?!_next/static/|_next/image/|favicon.ico).*"],
};