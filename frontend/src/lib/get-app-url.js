function withProtocol(url) {
	return url.startsWith("http") ? url : `https://${url}`;
}

export function getAppUrl() {
	// In production you should set this to your app URL.
	if (process.env.NEXT_PUBLIC_APP_URL) {
		return new URL(withProtocol(process.env.NEXT_PUBLIC_APP_URL));
	}

	// Automatically set by Vercel.
	if (process.env.NEXT_PUBLIC_VERCEL_URL) {
		return new URL(withProtocol(process.env.NEXT_PUBLIC_VERCEL_URL));
	}

	// If running in the browser environment we can use `window.location` to get the current URL.
	// eslint-disable-next-line unicorn/prefer-global-this
	if (typeof window !== "undefined") {
		// eslint-disable-next-line unicorn/prefer-global-this
		return new URL(window.location.origin);
	}

	// On the server, we could also use `headers()` to get the `x-forwarded-host` header and use that as the URL.
	// We did not use this approach because it can be easily spoofed and you need to trust the proxy to set this header
	// correctly and it could be a security risk if you're not careful.

	// Fallback to localhost. Change this to your local dev URL.
	return new URL(`http://localhost:${process.env.PORT || 3000}`);
}
