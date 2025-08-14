import "server-only";

import * as client from "openid-client";

// We cache the config because it makes a network request to fetch the OpenID configuration
// and we don't want to do that on every use of the config.
let clientConfig = null;

export async function createClientConfig() {
	if (clientConfig) {
		return clientConfig;
	}

	clientConfig = await client.discovery(
		new URL(process.env.NEXT_PUBLIC_COGNITO_AUTHORITY),
		process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID,
		process.env.COGNITO_CLIENT_SECRET
	);

	return clientConfig;
}
