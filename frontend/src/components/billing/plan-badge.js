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

	React.useEffect(() => {
		let active = true;
		(async () => {
			try {
				const token = (await getToken?.()) || null;
				const res = await fetch(`${API_URL}/billing/status`, {
					headers: token ? { Authorization: `Bearer ${token}` } : undefined,
					credentials: "include",
				});
				if (!res.ok) throw new Error(`Status ${res.status}`);
				const data = await res.json();
				if (!active) return;
				setState({ loading: false, plan: (data?.plan || "FREE").toString(), error: null });
			} catch (error) {
				if (!active) return;
				setState({ loading: false, plan: null, error });
			}
		})();
		return () => {
			active = false;
		};
	}, [getToken]);

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
