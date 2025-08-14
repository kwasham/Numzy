import { NextResponse } from "next/server";
import * as client from "openid-client";

import { paths } from "@/paths";
import { createClientConfig } from "@/lib/cognito/config";
import { getAppUrl } from "@/lib/get-app-url";

export async function GET() {
	const config = await createClientConfig();

	const codeChallengeMethod = "S256";
	const codeVerifier = client.randomPKCECodeVerifier();
	const codeChallenge = await client.calculatePKCECodeChallenge(codeVerifier);
	const nonce = client.randomNonce();

	const parameters = {
		redirect_uri: new URL(paths.auth.cognito.callback, getAppUrl()).toString(),
		scope: "email openid phone",
		code_challenge: codeChallenge,
		code_challenge_method: codeChallengeMethod,
		nonce,
	};

	const res = new NextResponse(undefined, { status: 307 });
	const cookieOptions = { httpOnly: true };
	res.cookies.set("code_verifier", codeVerifier, cookieOptions);
	res.cookies.set("nonce", nonce, cookieOptions);
	const redirectTo = client.buildAuthorizationUrl(config, parameters);
	res.headers.set("Location", redirectTo.toString());

	return res;
}
