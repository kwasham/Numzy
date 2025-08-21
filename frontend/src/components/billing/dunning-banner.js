"use client";

import React from "react";
import { useAuth } from "@clerk/nextjs";
import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import Button from "@mui/material/Button";

// no Stack needed here

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function DunningBanner({ onFix }) {
	const { getToken } = useAuth();
	const [state, setState] = React.useState({ loading: true, payment_state: null, action: null });

	const fetchStatus = React.useCallback(async () => {
		const token = (await getToken?.()) || null;
		const res = await fetch(`${API_URL}/billing/status`, {
			headers: token ? { Authorization: `Bearer ${token}` } : undefined,
			cache: "no-store",
		});
		if (!res.ok) throw new Error(`Status ${res.status}`);
		return res.json();
	}, [getToken]);

	React.useEffect(() => {
		let active = true;
		(async () => {
			try {
				const data = await fetchStatus();
				if (!active) return;
				setState({ loading: false, payment_state: data.payment_state || null, action: data.action || null });
			} catch {
				if (!active) return;
				setState({ loading: false, payment_state: null, action: null });
			}
		})();
		return () => {
			active = false;
		};
	}, [fetchStatus]);

	if (state.loading) return null;
	if (!state.payment_state || state.payment_state === "ok") return null;

	if (state.payment_state === "requires_action") {
		return (
			<Alert
				severity="warning"
				sx={{ alignItems: "center" }}
				action={
					<Button size="small" variant="outlined" onClick={onFix}>
						Complete payment
					</Button>
				}
			>
				<AlertTitle>Action required</AlertTitle>
				Your payment needs additional authentication to complete. Click Complete payment to continue.
			</Alert>
		);
	}

	if (state.payment_state === "past_due") {
		return (
			<Alert
				severity="error"
				sx={{ alignItems: "center" }}
				action={
					<Button size="small" variant="contained" onClick={onFix}>
						Fix payment
					</Button>
				}
			>
				<AlertTitle>Payment issue</AlertTitle>
				Your subscription is past due. Update your payment method to continue your plan.
			</Alert>
		);
	}

	return null;
}
