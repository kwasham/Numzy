import "server-only";

import { NextResponse } from "next/server";

import { paths } from "@/paths";
import { logger } from "@/lib/default-logger";
import { getAppUrl } from "@/lib/get-app-url";

import { createClient } from "./client";

export async function middleware(req) {
	const auth0Client = createClient();
	const res = await auth0Client.middleware(req);

	if (req.nextUrl.pathname.startsWith("/dashboard")) {
		const session = await auth0Client.getSession(req);

		if (!session) {
			logger.debug("[Middleware] User is not logged in, redirecting to sign in");
			const redirectTo = new URL(paths.auth.auth0.signIn, getAppUrl());
			redirectTo.searchParams.append("returnTo", paths.dashboard.overview);
			return NextResponse.redirect(redirectTo);
		}
	}

	return res;
}
