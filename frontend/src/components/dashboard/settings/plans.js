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
	const router = useRouter();
	const { getToken } = useAuth();
	const [state, setState] = React.useState({
		loading: true,
		currentPlanId: PlanId.FREE,
		catalog: null,
		selected: null,
		upgrading: false,
		yearly: false,
		preview: { loading: false, data: null, error: null, deferDowngrade: true },
		pendingPlan: null,
	});

	const toBackendPlan = React.useCallback((pid) => {
		if (!pid) return null;
		if (pid === PlanId.FREE) return "free";
		if (pid === PlanId.PERSONAL) return "personal";
		if (pid === PlanId.PRO) return "pro";
		if (pid === PlanId.BUSINESS) return "business";
		return String(pid).toLowerCase();
	}, []);

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
				const subscription = data?.subscription || {};
				const pendingPlan = subscription?.pending_plan ? mapPlanToCardId(subscription.pending_plan) : null;
				setState((prev) => ({ ...prev, loading: false, currentPlanId, catalog: data?.catalog ?? null, pendingPlan }));
			} catch {
				if (!active) return;
				setState((prev) => ({ ...prev, loading: false, currentPlanId: PlanId.FREE }));
			}
		})();
		return () => {
			active = false;
		};
	}, [fetchStatus]);

	const runPreview = React.useCallback(async () => {
		if (state.currentPlanId === PlanId.FREE) return;
		const target = state.selected;
		if (!target || target === state.currentPlanId) return;
		setState((p) => ({ ...p, preview: { ...p.preview, loading: true, error: null } }));
		try {
			const token = (await getToken?.()) || null;
			const res = await fetch(`${API_URL}/billing/subscription/preview`, {
				method: "POST",
				headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
				body: JSON.stringify({ target_plan: toBackendPlan(target), interval: state.yearly ? "yearly" : "monthly" }),
			});
			if (!res.ok) throw new Error(`Preview failed (${res.status})`);
			const data = await res.json();
			setState((p) => ({ ...p, preview: { ...p.preview, loading: false, data } }));
		} catch (error) {
			setState((p) => ({ ...p, preview: { ...p.preview, loading: false, error: error?.message || "Failed" } }));
		}
	}, [state.currentPlanId, state.selected, state.yearly, getToken, toBackendPlan]);

	React.useEffect(() => {
		runPreview();
	}, [runPreview]);

	const isDowngrade = React.useMemo(() => {
		if (state.preview.data) return !state.preview.data.is_upgrade;
		if (!state.selected || !state.catalog) return false;
		const cur = state.catalog?.[state.currentPlanId];
		const tgt = state.catalog?.[state.selected];
		if (!cur || !tgt) return false;
		const curPrice = cur?.monthly?.price || 0;
		const tgtPrice = tgt?.monthly?.price || 0;
		return tgtPrice < curPrice;
	}, [state.preview.data, state.selected, state.currentPlanId, state.catalog]);

	const handleSelect = (planId) => setState((p) => ({ ...p, selected: planId }));

	const handleApply = async () => {
		const target = state.selected;
		if (!target || target === state.currentPlanId) return;
		if (state.currentPlanId === PlanId.FREE) {
			setState((p) => ({ ...p, upgrading: true }));
			router.push(`/subscribe?plan=${encodeURIComponent(target)}&interval=${state.yearly ? "yearly" : "monthly"}`);
			setState((p) => ({ ...p, upgrading: false }));
			return;
		}
		setState((p) => ({ ...p, upgrading: true }));
		try {
			const token = (await getToken?.()) || null;
			const body = {
				target_plan: toBackendPlan(target),
				interval: state.yearly ? "yearly" : "monthly",
				defer_downgrade: isDowngrade && state.preview.deferDowngrade,
			};
			const res = await fetch(`${API_URL}/billing/subscription/change`, {
				method: "POST",
				headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
				body: JSON.stringify(body),
			});
			if (!res.ok) throw new Error(`Change failed (${res.status})`);
			await res.json();
			try {
				globalThis.sessionStorage?.setItem("numzy_plan_refresh_until", String(Date.now() + 60_000));
			} catch {
				/* ignore */
			}
			globalThis.location.reload();
		} catch (error) {
			alert(error?.message || "Unable to change plan");
		} finally {
			setState((p) => ({ ...p, upgrading: false }));
		}
	};

	const hasYearly = React.useMemo(() => {
		const cat = state.catalog || {};
		return availablePlans(cat, true).some((pid) => !!cat?.[pid]?.yearly?.price);
	}, [state.catalog]);

	const resolveDisplayPrice = (planId) => {
		const entry = state.catalog?.[planId];
		if (!entry) return FALLBACK_PRICES[planId];
		if (state.yearly && entry.yearly?.price) return entry.yearly.price / 12;
		return entry.monthly?.price ?? entry.price ?? FALLBACK_PRICES[planId];
	};

	const actionDisabled = !state.selected || state.selected === state.currentPlanId || state.upgrading;
	const actionLabel =
		state.currentPlanId === PlanId.FREE
			? "Subscribe"
			: isDowngrade
				? state.preview.deferDowngrade
					? "Schedule downgrade"
					: "Downgrade now"
				: "Apply change";

	return (
		<Card>
			<CardHeader
				avatar={
					<Avatar>
						<CreditCardIcon fontSize="var(--Icon-fontSize)" />
					</Avatar>
				}
				subheader={
					state.pendingPlan
						? `Downgrade to ${state.pendingPlan} scheduled for period end.`
						: "Select a plan. Downgrades can be scheduled for period end."
				}
				title="Plans"
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
								// Hide non-free plans if no price present in catalog (missing configuration)
								if (planId !== PlanId.FREE && !override?.monthly?.price && !override?.price) return null;
								const plan = { id: planId, name: base.name, currency, price };
								return (
									<Grid key={planId} size={{ md: 3, xs: 12 }}>
										<Box onClick={() => handleSelect(planId)}>
											<PlanCard isCurrent={planId === state.currentPlanId} plan={plan} />
											{state.pendingPlan && state.pendingPlan === planId && planId !== state.currentPlanId && (
												<Typography variant="caption" sx={{ color: "warning.main", pl: 1 }}>
													Scheduled
												</Typography>
											)}
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
						{/* Preview & action */}
						<Box sx={{ mt: 2 }}>
							{state.preview.loading && <Typography variant="body2">Computing preview…</Typography>}
							{state.preview.error && (
								<Typography variant="body2" color="error">
									Preview error: {state.preview.error}
								</Typography>
							)}
							{state.preview.data && (
								<Stack spacing={0.5} sx={{ mb: 1 }}>
									<Typography variant="body2">
										Current: {(state.preview.data.current_amount / 100).toFixed(2)}{" "}
										{state.preview.data.currency.toUpperCase()} / {state.preview.data.interval}
									</Typography>
									<Typography variant="body2">
										New: {(state.preview.data.new_amount / 100).toFixed(2)} {state.preview.data.currency.toUpperCase()}{" "}
										/ {state.preview.data.interval}
									</Typography>
									<Typography variant="body2" color={isDowngrade ? "warning.main" : "success.main"}>
										{isDowngrade ? "Downgrade" : "Upgrade"} difference:{" "}
										{(Math.abs(state.preview.data.difference) / 100).toFixed(2)}{" "}
										{state.preview.data.currency.toUpperCase()} per {state.preview.data.interval}
									</Typography>
								</Stack>
							)}
							{isDowngrade && state.currentPlanId !== PlanId.FREE && state.selected !== state.currentPlanId && (
								<Box sx={{ mb: 1 }}>
									<label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
										<input
											type="checkbox"
											checked={state.preview.deferDowngrade}
											onChange={() =>
												setState((p) => ({
													...p,
													preview: { ...p.preview, deferDowngrade: !p.preview.deferDowngrade },
												}))
											}
										/>
										<span style={{ fontSize: 12 }}>Schedule at period end (recommended)</span>
									</label>
								</Box>
							)}
							<Box sx={{ display: "flex", justifyContent: "flex-end" }}>
								<Button disabled={actionDisabled} onClick={handleApply} variant="contained">
									{state.upgrading ? (state.currentPlanId === PlanId.FREE ? "Redirecting…" : "Applying…") : actionLabel}
								</Button>
							</Box>
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
