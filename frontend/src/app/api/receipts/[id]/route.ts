import { revalidateTag } from "next/cache";
import { auth } from "@clerk/nextjs/server";

export const dynamic = "force-dynamic";

export async function GET(req: Request, ctx: { params: { id: string } | Promise<{ id: string }> }) {
	const { userId, getToken } = auth();
	const devBypass = process.env.DEV_AUTH_BYPASS === "true" || process.env.NEXT_PUBLIC_DEV_AUTH_BYPASS === "true";
	// Support Next.js experimental async params (must await) while remaining compatible with sync object.
	const rawParams = await ctx.params; // if already plain object, await is a no-op
	const receiptId = rawParams.id;
	const backend = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
	const urlObj = new URL(req.url);
	const tokenFromQuery = urlObj.searchParams.get("token");
	const headerToken = userId ? await getToken?.() : null;
	const token = headerToken || tokenFromQuery;
	const res = await fetch(`${backend}/receipts/${encodeURIComponent(receiptId)}`, {
		headers: token ? { Authorization: `Bearer ${token}` } : undefined,
		cache: "force-cache",
		next: userId ? { revalidate: 5, tags: [`receipt-${receiptId}`, `receipt-summary-${userId}`] } : { revalidate: 5 },
	});
	if (!res.ok) return new Response("not found", { status: res.status });
	const data = await res.json();
	return new Response(JSON.stringify(data), {
		status: 200,
		headers: {
			"content-type": "application/json",
			"x-receipt-mode": userId ? "auth" : devBypass ? "dev-bypass" : "anon",
		},
	});
}

export async function PATCH(req: Request, ctx: { params: { id: string } | Promise<{ id: string }> }) {
	const { userId, getToken } = auth();
	const rawParams = await ctx.params;
	const receiptId = rawParams.id;
	const backend = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
	// Try server-side token first; if absent, fall back to client-sent Authorization header
	const token = userId ? await getToken?.() : null;
	const incomingAuth = req.headers.get("authorization");
	// If Clerk server token isn't available but client sent Authorization, preserve it verbatim
	let forwardAuthHeader: string | undefined;
	if (token) {
		forwardAuthHeader = `Bearer ${token}`;
	} else if (incomingAuth) {
		forwardAuthHeader = incomingAuth; // already Bearer ...
	}
	let payload: unknown = null;
	try {
		payload = await req.json();
	} catch {
		payload = null;
	}
	const res = await fetch(`${backend}/receipts/${encodeURIComponent(receiptId)}`, {
		method: "PATCH",
		headers: {
			"Content-Type": "application/json",
			...(forwardAuthHeader ? { Authorization: forwardAuthHeader } : {}),
		},
		body: payload ? JSON.stringify(payload) : undefined,
		cache: "no-store",
	});
	const text = await res.text();
	if (res.ok) {
		// Revalidate detail + summary caches if we have userId tags
		try {
			if (userId) {
				revalidateTag(`receipt-${receiptId}`);
				revalidateTag(`receipt-summary-${userId}`);
			}
		} catch {
			// ignore JSON parse errors
		}
		return new Response(text, {
			status: res.status,
			headers: { "content-type": res.headers.get("content-type") || "application/json" },
		});
	}
	return new Response(text || "error", { status: res.status });
}

export async function DELETE(req: Request, ctx: { params: { id: string } | Promise<{ id: string }> }) {
	const { userId, getToken } = auth();
	const rawParams = await ctx.params;
	const receiptId = rawParams.id;
	const backend = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
	const token = userId ? await getToken?.() : null;
	const incomingAuth = req.headers.get("authorization");
	let forwardAuthHeader: string | undefined;
	if (token) forwardAuthHeader = `Bearer ${token}`;
	else if (incomingAuth) forwardAuthHeader = incomingAuth;
	const res = await fetch(`${backend}/receipts/${encodeURIComponent(receiptId)}`, {
		method: "DELETE",
		headers: forwardAuthHeader ? { Authorization: forwardAuthHeader } : undefined,
		cache: "no-store",
	});
	if (res.status === 204) {
		try {
			if (userId) {
				revalidateTag(`receipt-summary-${userId}`);
			}
		} catch {
			/* ignore */
		}
		return new Response(null, { status: 204 });
	}
	const text = await res.text();
	return new Response(text || "delete failed", { status: res.status });
}
