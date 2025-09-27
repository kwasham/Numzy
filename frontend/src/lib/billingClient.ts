// Lightweight client helpers for billing flows: status fetch, plan change, portal redirect.
// Uses fetch; assumes NEXT_PUBLIC_API_URL or relative proxy.

export interface BillingStatus {
	plan: string;
	subscription_status?: string | null;
	payment_state?: string | null;
	subscription?: { id?: string; status?: string; price_id?: string } | null;
	trial?: { active?: boolean; ends_at?: string | null; days_remaining?: number | null };
	catalog?: Record<string, any>;
}

function apiBase() {
	const raw = process.env.NEXT_PUBLIC_API_URL || "";
	if (!raw) return ""; // allow relative usage
	return raw.replace(/\/$/, "");
}

async function authHeader(getToken?: () => Promise<string | null | undefined>) {
	if (!getToken) return {};
	try {
		const t = await getToken();
		if (t) return { Authorization: `Bearer ${t}` };
	} catch {
		/* noop */
	}
	return {};
}

export async function fetchBillingStatus(
	getToken?: () => Promise<string | null | undefined>
): Promise<BillingStatus | null> {
	const base = apiBase();
	const headers: Record<string, string> = { "Content-Type": "application/json", ...(await authHeader(getToken)) };
	const url = base ? `${base}/billing/status` : `/billing/status`;
	try {
		const res = await fetch(url, { headers, credentials: "omit", mode: "cors" });
		if (!res.ok) return null;
		return await res.json();
	} catch {
		return null;
	}
}

export interface ChangePlanOptions {
	targetPlan: "personal" | "pro" | "business";
	interval?: "monthly" | "yearly";
	prorationBehavior?: "create_prorations" | "none" | "always_invoice" | "none_implicit";
	deferDowngrade?: boolean; // schedule downgrade at period end
}

export async function changeSubscriptionPlan(
	opts: ChangePlanOptions,
	getToken?: () => Promise<string | null | undefined>
): Promise<{ ok: boolean; status?: number; body?: any }> {
	const base = apiBase();
	const headers: Record<string, string> = { "Content-Type": "application/json", ...(await authHeader(getToken)) };
	const url = base ? `${base}/billing/subscription/change` : `/billing/subscription/change`;
	const body = {
		target_plan: opts.targetPlan,
		...(opts.interval ? { interval: opts.interval } : {}),
		...(opts.prorationBehavior ? { proration_behavior: opts.prorationBehavior } : {}),
		...(typeof opts.deferDowngrade === "boolean" ? { defer_downgrade: opts.deferDowngrade } : {}),
	};
	try {
		const res = await fetch(url, {
			method: "POST",
			headers,
			credentials: "omit",
			mode: "cors",
			body: JSON.stringify(body),
		});
		const txt = await res.text();
		let parsed: any;
		try {
			parsed = JSON.parse(txt);
		} catch {
			parsed = txt;
		}
		return { ok: res.ok, status: res.status, body: parsed };
	} catch (error) {
		return { ok: false, body: { error: (error as any)?.message } };
	}
}

export async function createPortalSession(getToken?: () => Promise<string | null | undefined>): Promise<string | null> {
	const base = apiBase();
	const headers: Record<string, string> = { "Content-Type": "application/json", ...(await authHeader(getToken)) };
	const url = base ? `${base}/billing/portal` : `/billing/portal`;
	try {
		const res = await fetch(url, { method: "POST", headers, credentials: "omit", mode: "cors" });
		if (!res.ok) return null;
		const data = await res.json();
		return data?.url || null;
	} catch {
		return null;
	}
}
