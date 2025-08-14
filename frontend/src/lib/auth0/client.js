import "server-only";

import { Auth0Client } from "@auth0/nextjs-auth0/server";

import { paths } from "@/paths";
import { getAppUrl } from "@/lib/get-app-url";

export function createClient() {
	// Read the notes from https://github.com/auth0/nextjs-auth0/tree/v4.0.0-beta.14?tab=readme-ov-file#customizing-the-client
	const auth0Config = {
		domain: process.env.AUTH0_DOMAIN,
		clientId: process.env.AUTH0_CLIENT_ID,
		clientSecret: process.env.AUTH0_CLIENT_SECRET,
		secret: process.env.AUTH0_SECRET,
		appBaseUrl: getAppUrl().toString(),
		routes: {
			login: paths.auth.auth0.signIn,
			logout: paths.auth.auth0.signOut,
			callback: paths.auth.auth0.callback,
		},
	};

	return new Auth0Client(auth0Config);
}
