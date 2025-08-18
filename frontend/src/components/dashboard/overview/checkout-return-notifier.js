"use client";

import React from "react";
import { toast } from "sonner";

export function CheckoutReturnNotifier() {
	React.useEffect(() => {
		if (typeof globalThis === "undefined" || !globalThis.location) return;
		const url = new URL(globalThis.location.href);
		const flag = url.searchParams.get("checkout");
		if (flag === "success") {
			// Hint other components (e.g., PlanBadge) to refresh status for up to 60s
			try {
				const until = Date.now() + 60_000;
				globalThis.sessionStorage?.setItem("numzy_plan_refresh_until", String(until));
			} catch {
				/* ignore */
			}
			toast.success("Checkout complete. Your plan will update shortly.");
			url.searchParams.delete("checkout");
			globalThis.history.replaceState({}, "", url.toString());
		} else if (flag === "cancelled") {
			toast.info("Checkout canceled.");
			url.searchParams.delete("checkout");
			globalThis.history.replaceState({}, "", url.toString());
		}
	}, []);
	return null;
}
