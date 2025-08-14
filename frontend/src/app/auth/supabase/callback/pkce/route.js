import { NextResponse } from "next/server";
import { AuthApiError } from "@supabase/supabase-js";

import { paths } from "@/paths";
import { logger } from "@/lib/default-logger";
import { createClient } from "@/lib/supabase/server";

// NOTE: If you have a proxy in front of this app
//  the request origin might be a local address.
//  Consider using `appConfig.url` from `@/config` instead.

// NOTE: This is not a `Page` because we only redirect and it will never render React content.

export async function GET(req) {
	const { searchParams, origin } = req.nextUrl;

	if (searchParams.get("error")) {
		return NextResponse.json({ error: searchParams.get("error_description") || "Something went wrong" });
	}

	const code = searchParams.get("code");

	if (!code) {
		return NextResponse.json({ error: "Code is missing" });
	}

	const supabaseClient = await createClient();

	try {
		const { error } = await supabaseClient.auth.exchangeCodeForSession(code);

		if (error) {
			return NextResponse.json({ error: error.message });
		}
	} catch (error) {
		if (error instanceof AuthApiError && error.message.includes("code and code verifier should be non-empty")) {
			return NextResponse.json({ error: "Please open the link in the same browser" });
		}

		logger.error("Callback error", error);

		return NextResponse.json({ error: "Something went wrong" });
	}

	const next = searchParams.get("next") || paths.home;

	return NextResponse.redirect(new URL(next, origin));
}
