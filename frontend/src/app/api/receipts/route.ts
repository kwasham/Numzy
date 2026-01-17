import { auth } from "@clerk/nextjs/server";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
	const { userId, getToken } = auth();
	const backend = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
	// Prefer server-side token if available; otherwise, forward the incoming Authorization header.
	let forwardAuthHeader: string | undefined;
	try {
		if (userId) {
			const token = await getToken?.();
			if (token) forwardAuthHeader = `Bearer ${token}`;
		}
	} catch {
		/* ignore */
	}
	const incomingAuth = req.headers.get("authorization");
	if (!forwardAuthHeader && incomingAuth) {
		forwardAuthHeader = incomingAuth;
	}

	// Accept multipart/form-data and forward it as-is to backend
	let form: FormData;
	try {
		form = await req.formData();
	} catch {
		return new Response("invalid form data", { status: 400 });
	}

	// Support Clerk token via query param as a fallback (backend supports ?token=)
	const url = new URL(req.url);
	const queryToken = url.searchParams.get("token");
	const targetUrl = queryToken ? `${backend}/receipts?token=${encodeURIComponent(queryToken)}` : `${backend}/receipts`;

	const res = await fetch(targetUrl, {
		method: "POST",
		body: form,
		headers: {
			...(forwardAuthHeader ? { Authorization: forwardAuthHeader } : {}),
		},
		// Avoid caching uploads
		cache: "no-store",
	});
	const contentType = res.headers.get("content-type") || "application/json";
	const text = await res.text();
	return new Response(text, { status: res.status, headers: { "content-type": contentType } });
}
