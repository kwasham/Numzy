import { NextResponse } from "next/server";

import { appConfig } from "@/config/app";
import { AuthStrategy } from "@/lib/auth-strategy";

export async function middleware(req) {
	// Optional root redirect (no root page component). Remove if you prefer a 404 at '/'.
	if (req.nextUrl.pathname === "/") {
		const url = req.nextUrl.clone();
		url.pathname = "/dashboard";
		return NextResponse.redirect(url);
	}
	switch (appConfig.authStrategy) {
		case AuthStrategy.AUTH0: {
			const mod = await import("@/lib/auth0/middleware");
			return mod.middleware(req);
		}
		case AuthStrategy.CLERK: {
			const mod = await import("@/lib/clerk/middleware");
			return mod.middleware(req);
		}
		case AuthStrategy.COGNITO: {
			const mod = await import("@/lib/cognito/middleware");
			return mod.middleware(req);
		}
		case AuthStrategy.CUSTOM: {
			const mod = await import("@/lib/custom-auth/middleware");
			return mod.middleware(req);
		}
		case AuthStrategy.SUPABASE: {
			const mod = await import("@/lib/supabase/middleware");
			return mod.middleware(req);
		}
		default: {
			return NextResponse.next({ request: req });
		}
	}
}

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
