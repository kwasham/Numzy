"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import Divider from "@mui/material/Divider";
import Grid from "@mui/material/Grid";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { CreditCardIcon } from "@phosphor-icons/react/dist/ssr/CreditCard";
import { PencilSimpleIcon } from "@phosphor-icons/react/dist/ssr/PencilSimple";

import { PropertyItem } from "@/components/core/property-item";
import { PropertyList } from "@/components/core/property-list";

import { PlanCard } from "./plan-card";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const plans = [
	{ id: "startup", name: "Free", currency: "USD", price: 0 },
	{ id: "standard", name: "Pro", currency: "USD", price: 14.99 },
	{ id: "business", name: "Team", currency: "USD", price: 29.99 },
];

function mapPlanToCardId(planName) {
	// Normalize and map backend plan values to our UI card ids
	const p = String(planName || "").toUpperCase();
	if (p === "FREE") return "startup";
	if (p === "PRO") return "standard";
	if (p === "BUSINESS" || p === "ENTERPRISE") return "business";
	// Default to startup when unknown
	return "startup";
}

export function Plans() {
	const { getToken } = useAuth();
	const router = useRouter();
	const [state, setState] = React.useState({
		loading: true,
		currentPlanId: "startup",
		catalog: null,
		selected: null,
		upgrading: false,
	});

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
		(async () => {
			try {
				const data = await fetchStatus();
				if (!active) return;
				const currentPlanId = mapPlanToCardId(data?.plan);
				setState((prev) => ({ ...prev, loading: false, currentPlanId, catalog: data?.catalog ?? null }));
			} catch {
				if (!active) return;
				// Fallback to startup on error
				setState((prev) => ({ ...prev, loading: false, currentPlanId: "startup" }));
			}
		})();
		return () => {
			active = false;
		};
	}, [fetchStatus]);

	const handleSelect = (planId) => {
		setState((prev) => ({ ...prev, selected: planId }));
	};

	const handleUpgrade = async () => {
		const target = state.selected || state.currentPlanId;
		// No-op if selecting current plan or FREE
		if (target === state.currentPlanId || target === "startup") return;
		setState((prev) => ({ ...prev, upgrading: true }));
		// Navigate to custom Elements checkout page, pass plan in query
		router.push(`/subscribe?plan=${encodeURIComponent(target)}`);
		setState((prev) => ({ ...prev, upgrading: false }));
	};

	return (
		<Card>
			<CardHeader
				avatar={
					<Avatar>
						<CreditCardIcon fontSize="var(--Icon-fontSize)" />
					</Avatar>
				}
				subheader="You can upgrade and downgrade whenever you want."
				title="Change plan"
			/>
			<CardContent>
				<Stack divider={<Divider />} spacing={3}>
					<Stack spacing={3}>
						<Grid container spacing={3}>
							{plans.map((plan) => {
								const override = state.catalog?.[plan.id];
								const displayPlan = override
									? {
											...plan,
											price: typeof override.price === "number" ? override.price : plan.price,
											currency: override.currency || plan.currency,
										}
									: plan;
								return (
									<Grid
										key={plan.id}
										size={{
											md: 4,
											xs: 12,
										}}
									>
										<Box onClick={() => handleSelect(plan.id)}>
											<PlanCard isCurrent={plan.id === state.currentPlanId} plan={displayPlan} />
										</Box>
									</Grid>
								);
							})}
						</Grid>
						<Box sx={{ display: "flex", justifyContent: "flex-end" }}>
							<Button onClick={handleUpgrade} disabled={state.upgrading} variant="contained">
								{state.upgrading ? "Redirecting…" : "Upgrade plan"}
							</Button>
						</Box>
					</Stack>
					<Stack spacing={3}>
						<Stack direction="row" spacing={3} sx={{ alignItems: "center", justifyContent: "space-between" }}>
							<Typography variant="h6">Billing details</Typography>
							<Button color="secondary" startIcon={<PencilSimpleIcon />}>
								Edit
							</Button>
						</Stack>
						<Card sx={{ borderRadius: 1 }} variant="outlined">
							<PropertyList divider={<Divider />} sx={{ "--PropertyItem-padding": "12px 24px" }}>
								{[
									{ key: "Name", value: "Sofia Rivers" },
									{ key: "Country", value: "Germany" },
									{ key: "State", value: "Brandenburg" },
									{ key: "City", value: "Berlin" },
									{ key: "Zip Code", value: "667123" },
									{ key: "Card Number", value: "**** 1111" },
								].map((item) => (
									<PropertyItem key={item.key} name={item.key} value={item.value} />
								))}
							</PropertyList>
						</Card>
						<Typography color="text.secondary" variant="body2">
							We cannot refund once you purchased a subscription, but you can always{" "}
							<Link variant="inherit">cancel</Link>
						</Typography>
					</Stack>
				</Stack>
			</CardContent>
		</Card>
	);
}
