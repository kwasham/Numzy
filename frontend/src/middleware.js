import { NextResponse } from "next/server";

import { appConfig } from "@/config/app";
import { AuthStrategy } from "@/lib/auth-strategy";
import { middleware as auth0Middleware } from "@/lib/auth0/middleware";
import { middleware as clerkMiddleware } from "@/lib/clerk/middleware";
import { middleware as cognitoMiddleware } from "@/lib/cognito/middleware";
import { middleware as customAuthMiddleware } from "@/lib/custom-auth/middleware";
import { middleware as supabaseMiddleware } from "@/lib/supabase/middleware";

let middleware = async (req) => {
	return NextResponse.next({ request: req });
};

if (appConfig.authStrategy === AuthStrategy.AUTH0) {
	middleware = auth0Middleware;
}

if (appConfig.authStrategy === AuthStrategy.CLERK) {
	middleware = clerkMiddleware;
}

if (appConfig.authStrategy === AuthStrategy.COGNITO) {
	middleware = cognitoMiddleware;
}

if (appConfig.authStrategy === AuthStrategy.CUSTOM) {
	middleware = customAuthMiddleware;
}

if (appConfig.authStrategy === AuthStrategy.SUPABASE) {
	middleware = supabaseMiddleware;
}

export { middleware };

export const config = {
	matcher: [
		/*
		 * Match all request paths except for the ones starting with:
		 * - _next/static (static files)
		 * - _next/image (image optimization files)
		 * - favicon.ico, sitemap.xml, robots.txt (metadata files)
		 */
		"/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
	],
};
