import { cookies, headers } from "next/headers";

function getOrigin() {
	const h = headers();
	const proto = h.get("x-forwarded-proto") || process.env.NEXT_INTERNAL_PROTO || "http";
	const host = h.get("x-forwarded-host") || h.get("host") || process.env.NEXT_INTERNAL_HOST;
	if (!host) {
		const fallback = process.env.NEXT_PUBLIC_APP_URL || process.env.APP_URL;
		if (fallback) return fallback.replace(/\/$/, "");
		return `${proto}://localhost:3000`;
	}
	return `${proto}://${host}`;
}

function buildUrl(path: string) {
	if (/^https?:/i.test(path)) return path;
	const origin = getOrigin();
	return `${origin}${path.startsWith("/") ? "" : "/"}${path}`;
}

export function withAuthHeaders(init: RequestInit = {}) {
	const cookieStore = cookies();
	const cookieHeader = cookieStore.toString();
	const headersInit = new Headers(init.headers || undefined);
	if (cookieHeader && !headersInit.has("cookie")) headersInit.set("cookie", cookieHeader);
	return { ...init, headers: headersInit } satisfies RequestInit;
}

export async function fetchInternal(path: string, init: RequestInit = {}) {
	const url = buildUrl(path);
	return fetch(url, withAuthHeaders(init));
}
