"use client";

import React from "react";
import { useAuth } from "@clerk/nextjs";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function PlanBadge({ size = "small" }) {
	const { getToken } = useAuth();
	const [state, setState] = React.useState({ loading: true, plan: null, error: null });

	const fetchStatus = React.useCallback(async () => {
		const token = (await getToken?.()) || null;
		const res = await fetch(`${API_URL}/billing/status`, {
			headers: token ? { Authorization: `Bearer ${token}` } : undefined,
			credentials: "include",
		});
		if (!res.ok) throw new Error(`Status ${res.status}`);
		return res.json();
	}, [getToken]);

	React.useEffect(() => {
		let active = true;
		let timer = null;

		const run = async () => {
			try {
				const data = await fetchStatus();
				if (!active) return;
				const plan = (data?.plan || "FREE").toString();
				setState({ loading: false, plan, error: null });

				// If we are within the refresh window, keep polling every 5s until plan != FREE
				const until = Number(globalThis.sessionStorage?.getItem("numzy_plan_refresh_until") || 0);
				const now = Date.now();
				const withinWindow = until && now < until;
				if (withinWindow && plan === "FREE") {
					timer = globalThis.setTimeout(run, 5000);
				} else if (withinWindow && plan !== "FREE") {
					// Plan upgraded within window; clear flag and stop polling
					try {
						globalThis.sessionStorage?.removeItem("numzy_plan_refresh_until");
					} catch (error) {
						void error;
					}
				} else if (!withinWindow) {
					// Clear the flag once window elapsed
					try {
						globalThis.sessionStorage?.removeItem("numzy_plan_refresh_until");
					} catch (error) {
						void error;
					}
				}
			} catch (error) {
				if (!active) return;
				setState((prev) => ({ ...prev, loading: false, error }));
			}
		};

		run();
		return () => {
			active = false;
			if (timer) globalThis.clearTimeout(timer);
		};
	}, [fetchStatus]);

	if (state.loading) {
		return (
			<Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
				<CircularProgress size={14} />
				<Chip size={size} variant="outlined" label="Plan: ..." />
			</Stack>
		);
	}

	const label = state.plan ? `Plan: ${state.plan}` : "Plan: Unknown";
	const color =
		state.plan === "PRO" || state.plan === "BUSINESS" || state.plan === "ENTERPRISE" ? "primary" : "default";

	return <Chip size={size} color={color} variant="outlined" label={label} />;
}
