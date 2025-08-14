import { NextResponse } from "next/server";
import * as client from "openid-client";

import { paths } from "@/paths";
import { createClientConfig } from "@/lib/cognito/config";
import { getAppUrl } from "@/lib/get-app-url";

export async function GET(req) {
	const codeVerifier = req.cookies.get("code_verifier")?.value;
	const nonce = req.cookies.get("nonce")?.value;

	if (!codeVerifier || !nonce) {
		return new NextResponse(JSON.stringify({ error: "Missing code_verifier or nonce" }), { status: 400 });
	}

	const config = await createClientConfig();

	let tokens;

	try {
		tokens = await client.authorizationCodeGrant(config, new URL(req.url), {
			pkceCodeVerifier: codeVerifier,
			expectedNonce: nonce,
			idTokenExpected: true,
		});
	} catch {
		return new NextResponse(JSON.stringify({ error: "Failed to exchange authorization code for tokens" }), {
			status: 400,
		});
	}

	const res = new NextResponse(undefined, { status: 307 });

	// Cleanup cookies
	res.cookies.delete("code_verifier");
	res.cookies.delete("nonce");

	const claims = tokens.claims();

	// Persist tokens
	const cookieOptions = { httpOnly: true };

	if (claims?.sub) {
		res.cookies.set("sub", claims.sub, cookieOptions);
	}

	res.cookies.set("access_token", tokens.access_token, cookieOptions);

	if (tokens.id_token) {
		res.cookies.set("id_token", tokens.id_token, cookieOptions);
	}

	if (tokens.refresh_token) {
		res.cookies.set("refresh_token", tokens.refresh_token, cookieOptions);
	}

	const redirectTo = new URL(paths.dashboard.overview, getAppUrl());
	res.headers.set("Location", redirectTo.toString());

	return res;
}
