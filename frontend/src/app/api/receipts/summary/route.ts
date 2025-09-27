import { auth } from "@clerk/nextjs/server";

// Revalidate via fetch options; this file itself is dynamic only when fetched.
export const dynamic = "force-dynamic"; // allow per-user auth segmentation

export async function GET(req: Request) {
	const { userId, getToken } = auth();
	const url = new URL(req.url);
	const limit = url.searchParams.get("limit") || "100";
	const backend = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

	// Require auth; do not serve anon cached data via internal route
	if (!userId) {
		return new Response(JSON.stringify([]), {
			status: 200,
			headers: {
				"content-type": "application/json",
				"x-receipts-summary-mode": "anon-empty",
			},
		});
	}
	const token = await getToken?.();
	if (!token) {
		return new Response(JSON.stringify([]), {
			status: 200,
			headers: {
				"content-type": "application/json",
				"x-receipts-summary-mode": "anon-empty",
			},
		});
	}

	const backendUrl = `${backend}/receipts/summary?limit=${encodeURIComponent(limit)}`;
	const res = await fetch(backendUrl, {
		headers: { Authorization: `Bearer ${token}` },
		cache: "no-store",
	});
	if (!res.ok) {
		return new Response(JSON.stringify([]), {
			status: 200,
			headers: {
				"content-type": "application/json",
				"x-receipts-summary-mode": "auth",
			},
		});
	}
	const data = await res.json();
	return new Response(JSON.stringify(data), {
		status: 200,
		headers: {
			"content-type": "application/json",
			"x-receipts-summary-mode": "auth",
		},
	});
}
