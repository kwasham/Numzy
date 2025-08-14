import "server-only";

import { NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

import { paths } from "@/paths";
import { logger } from "@/lib/default-logger";
import { getAppUrl } from "@/lib/get-app-url";

export async function middleware(req) {
	let res = NextResponse.next({ request: req });

	const supabaseClient = createServerClient(
		process.env.NEXT_PUBLIC_SUPABASE_URL,
		process.env.NEXT_PUBLIC_SUPABASE_PUBLIC_KEY,
		{
			cookies: {
				getAll() {
					return req.cookies.getAll();
				},
				setAll(cookiesToSet) {
					for (const { name, value } of cookiesToSet) {
						req.cookies.set(name, value);
					}

					res = NextResponse.next({ request: req });

					for (const { name, value, options } of cookiesToSet) {
						res.cookies.set(name, value, options);
					}
				},
			},
		}
	);

	if (req.nextUrl.pathname.startsWith("/dashboard")) {
		const { data } = await supabaseClient.auth.getUser();

		if (!data.user) {
			logger.debug("[Middleware] User is not logged in, redirecting to sign in");
			const redirectTo = new URL(paths.auth.supabase.signIn, getAppUrl());
			return NextResponse.redirect(redirectTo);
		}
	}

	return res;
}
