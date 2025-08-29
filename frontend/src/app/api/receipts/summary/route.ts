import { auth } from "@clerk/nextjs/server";

// Revalidate via fetch options; this file itself is dynamic only when fetched.
export const dynamic = "force-dynamic"; // allow per-user auth segmentation

export async function GET(req: Request) {
	const { userId, getToken } = auth();
	// In development (or when backend DEV_AUTH_BYPASS is enabled) we still want data even if
	// Clerk userId is absent (eg. missing publishable key locally). Fallback to backend summary fetch.
	const devBypass = process.env.DEV_AUTH_BYPASS === "true" || process.env.NEXT_PUBLIC_DEV_AUTH_BYPASS === "true";
	const url = new URL(req.url);
	const limit = url.searchParams.get("limit") || "100";
	const backend = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
	const token = userId ? await getToken?.() : null;
	const backendUrl = `${backend}/receipts/summary?limit=${encodeURIComponent(limit)}`;
	const res = await fetch(backendUrl, {
		headers: token ? { Authorization: `Bearer ${token}` } : undefined,
		cache: "force-cache",
		next: userId ? { revalidate: 5, tags: [`receipt-summary-${userId}`] } : { revalidate: 5 },
	});
	if (!res.ok) {
		return new Response(JSON.stringify([]), {
			status: 200,
			headers: {
				"content-type": "application/json",
				"x-receipts-summary-mode": userId ? "auth" : devBypass ? "dev-bypass" : "anon",
			},
		});
	}
	const data = await res.json();
	// If unauthenticated (no userId) we don't tag per-user cache; downstream code treats as anonymous/dev data.
	return new Response(JSON.stringify(data), {
		status: 200,
		headers: {
			"content-type": "application/json",
			"x-receipts-summary-mode": userId ? "auth" : devBypass ? "dev-bypass" : "anon",
		},
	});
}
