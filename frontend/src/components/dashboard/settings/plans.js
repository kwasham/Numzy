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
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";
import { CreditCardIcon } from "@phosphor-icons/react/dist/ssr/CreditCard";
import { PencilSimpleIcon } from "@phosphor-icons/react/dist/ssr/PencilSimple";

import { PropertyItem } from "@/components/core/property-item";
import { PropertyList } from "@/components/core/property-list";

import { availablePlans, PLAN_CAPABILITIES, PlanId } from "../../../../../shared/types/plan";
import { PlanCard } from "./plan-card";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Local fallback prices used only if backend catalog lacks entries (development safety)
const FALLBACK_PRICES = {
	[PlanId.FREE]: 0,
	[PlanId.PERSONAL]: 9.99,
	[PlanId.PRO]: 29,
	[PlanId.BUSINESS]: 99,
};

function mapPlanToCardId(planName) {
	// Normalize backend enum (FREE, PERSONAL, PRO, BUSINESS, ENTERPRISE) to UI IDs
	const p = String(planName || "").toUpperCase();
	if (p === "FREE") return PlanId.FREE;
	if (p === "PERSONAL") return PlanId.PERSONAL;
	if (p === "PRO") return PlanId.PRO;
	if (p === "BUSINESS" || p === "ENTERPRISE") return PlanId.BUSINESS; // enterprise visually treated as business
	return PlanId.FREE; // default
}

export function Plans() {
	const { getToken } = useAuth();
	const router = useRouter();
	const [state, setState] = React.useState({
		loading: true,
		currentPlanId: PlanId.FREE,
		catalog: null,
		selected: null,
		upgrading: false,
		yearly: false,
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
				// Fallback to free on error
				setState((prev) => ({ ...prev, loading: false, currentPlanId: "free" }));
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
		if (target === state.currentPlanId || target === PlanId.FREE) return;
		setState((prev) => ({ ...prev, upgrading: true }));
		// Navigate to custom Elements checkout page, pass plan in query
		router.push(`/subscribe?plan=${encodeURIComponent(target)}`);
		setState((prev) => ({ ...prev, upgrading: false }));
	};

	const hasYearly = React.useMemo(() => {
		const cat = state.catalog || {};
		return availablePlans(cat, true).some((pid) => !!cat?.[pid]?.yearly?.price);
	}, [state.catalog]);

	const resolveDisplayPrice = (planId) => {
		const entry = state.catalog?.[planId];
		if (!entry) return FALLBACK_PRICES[planId];
		if (state.yearly && entry.yearly?.price) return entry.yearly.price / 12; // per-month equivalent
		return entry.monthly?.price ?? entry.price ?? FALLBACK_PRICES[planId];
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
					{hasYearly && (
						<Box sx={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 1 }}>
							<Typography variant="body2">Monthly</Typography>
							<Switch
								size="small"
								checked={state.yearly}
								onChange={() => setState((p) => ({ ...p, yearly: !p.yearly }))}
							/>
							<Typography variant="body2">
								Yearly{" "}
								{state.yearly && (
									<Box component="span" sx={{ color: "success.main" }}>
										Save
									</Box>
								)}
							</Typography>
						</Box>
					)}
					<Stack spacing={3}>
						<Grid container spacing={3}>
							{availablePlans(state.catalog || {}, true).map((planId) => {
								const base = PLAN_CAPABILITIES[planId];
								const override = state.catalog?.[planId] || {};
								const currency = override?.currency || "USD";
								const price = resolveDisplayPrice(planId);
								const plan = { id: planId, name: base.name, currency, price };
								return (
									<Grid key={planId} size={{ md: 3, xs: 12 }}>
										<Box onClick={() => handleSelect(planId)}>
											<PlanCard isCurrent={planId === state.currentPlanId} plan={plan} />
											{/* Capabilities summary (quick glance) */}
											<Stack sx={{ px: 1, pt: 1 }} spacing={0.5}>
												<Typography variant="caption">Quota: {base.monthlyQuota}</Typography>
												<Typography variant="caption">
													Retention: {base.retentionDays === "custom" ? "Custom" : base.retentionDays + "d"}
												</Typography>
												{base.prioritySupport && <Typography variant="caption">Priority support</Typography>}
												{base.sso && <Typography variant="caption">SSO</Typography>}
											</Stack>
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
