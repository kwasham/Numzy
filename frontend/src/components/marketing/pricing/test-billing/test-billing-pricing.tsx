"use client";

import * as React from "react";
import { useAuth } from "@clerk/nextjs";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { FEATURE_DETAILS } from "@shared/pricing/featureDetails";

import {
	generatePlanFeatures,
	PLAN_METADATA,
	planPrice,
	priceMeta,
} from "@/components/marketing/pricing/pricing-config";

// NOTE: This is a lightweight experimental / test billing page component inspired by external pricing layouts.
// It intentionally does NOT copy any proprietary styling verbatim. Feel free to iterate / discard.

interface PlanDescriptor {
	id: string;
	name: string;
	description: string;
	price: number;
	monthlyRef?: number;
	discountPercent?: number;
	recommended?: boolean;
	features: string[];
}

const PAID_PLAN_IDS = ["personal", "pro", "business"]; // omit free for trial-first strategy

export function TestBillingPricing() {
	const { getToken } = useAuth();
	const [yearly, setYearly] = React.useState(false);
	const [checkingOut, setCheckingOut] = React.useState<string | null>(null);
	const [error, setError] = React.useState<string | null>(null);
	const isYear = yearly;

	const plans: PlanDescriptor[] = React.useMemo(() => {
		return PAID_PLAN_IDS.map((id) => {
			const meta = priceMeta(id);
			const price = planPrice(id, { yearly: isYear });
			const monthlyRef = isYear ? meta.annualMonthly : undefined;
			const discountPercent = isYear ? meta.discountPercent : undefined;
			return {
				id,
				name: PLAN_METADATA[id].name,
				description: PLAN_METADATA[id].description,
				price,
				monthlyRef,
				discountPercent,
				recommended: id === "pro", // mark Pro as recommended by default
				features: generatePlanFeatures(id).filter((f) => f !== "—"),
			};
		});
	}, [isYear]);

	async function startCheckout(planId: string) {
		setError(null);
		setCheckingOut(planId);
		try {
			// Map plan -> price env var
			const envMap: Record<string, string | undefined> = {
				personal: process.env.NEXT_PUBLIC_STRIPE_PRICE_PERSONAL_MONTHLY,
				pro: process.env.NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY,
				business:
					process.env.NEXT_PUBLIC_STRIPE_PRICE_BUSINESS_MONTHLY || process.env.NEXT_PUBLIC_STRIPE_PRICE_TEAM_MONTHLY,
			};
			const priceId = envMap[planId];
			if (!priceId) {
				setError(`Missing price id env var for ${planId}`);
				return;
			}
			const token = (await getToken?.()) || null;
			const idempotency = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
			const apiBase = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "") || "";
			const url = apiBase ? `${apiBase}/billing/checkout` : "/billing/checkout";
			const res = await fetch(url, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					"Idempotency-Key": idempotency,
					...(token ? { Authorization: `Bearer ${token}` } : {}),
				},
				body: JSON.stringify({ price_id: priceId }),
				credentials: "omit",
				mode: "cors",
			});
			if (res.status === 409) {
				// Already subscribed -> redirect to settings billing page
				globalThis.location.href = "/dashboard/settings/billing?already_subscribed=1";
				return;
			}
			if (!res.ok) {
				const txt = await res.text();
				setError(`Checkout failed (${res.status}) ${txt}`);
				return;
			}
			const data = await res.json();
			if (data?.url) {
				globalThis.location.href = data.url;
			} else {
				setError("No redirect URL returned");
			}
		} catch (error_) {
			setError((error_ as Error)?.message || "Unexpected error");
		} finally {
			setCheckingOut(null);
		}
	}

	return (
		<Box sx={{ width: "100%", py: { xs: 6, md: 10 } }}>
			<Stack spacing={6} sx={{ maxWidth: 1360, mx: "auto", px: { xs: 2, md: 4 } }}>
				{/* Header */}
				<Stack spacing={2} sx={{ textAlign: "center", maxWidth: 760, mx: "auto" }}>
					<Typography variant="h3" component="h1" sx={{ fontWeight: 600 }}>
						Choose the plan built for your scale
					</Typography>
					<Typography variant="body1" color="text.secondary">
						Transparent usage-based tiers. Start a trial and upgrade seamlessly when you need more.
					</Typography>
					<Stack direction="row" spacing={2} sx={{ alignItems: "center", justifyContent: "center", pt: 1 }}>
						<Typography variant="body2">Monthly</Typography>
						<Switch
							checked={yearly}
							onChange={() => setYearly((p) => !p)}
							inputProps={{ "aria-label": "Toggle annual billing" }}
						/>
						<Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
							<Typography variant="body2">Annual</Typography>
							{yearly && <Chip size="small" color="success" label="Save" />}
						</Stack>
					</Stack>
				</Stack>
				{/* Plans Grid */}
				<Grid container spacing={3}>
					{plans.map((p) => {
						const priceDisplay = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(p.price);
						return (
							<Grid key={p.id} size={{ xs: 12, sm: 6, md: 4 }}>
								<Box
									sx={{
										position: "relative",
										borderRadius: 3,
										p: 3,
										height: "100%",
										display: "flex",
										flexDirection: "column",
										gap: 2,
										bgcolor: "background.paper",
										border: "1px solid",
										borderColor: p.recommended ? "primary.main" : "divider",
										boxShadow: p.recommended ? 6 : 1,
										transition: "box-shadow .2s ease, transform .2s ease",
										"&:hover": { boxShadow: 10, transform: "translateY(-4px)" },
									}}
								>
									{p.recommended && (
										<Chip
											size="small"
											color="primary"
											label="Recommended"
											sx={{ position: "absolute", top: 12, right: 12 }}
										/>
									)}
									<Stack spacing={1}>
										<Typography variant="h5" sx={{ fontWeight: 600 }}>
											{p.name}
										</Typography>
										<Typography variant="body2" color="text.secondary">
											{p.description}
										</Typography>
									</Stack>
									<Stack spacing={0.5}>
										<Stack direction="row" spacing={1} sx={{ alignItems: "flex-end" }}>
											<Typography variant="h3" component="span">
												{priceDisplay}
											</Typography>
											<Typography variant="h6" component="span">
												/mo
											</Typography>
										</Stack>
										{p.monthlyRef != null && (
											<Typography variant="caption" color="text.secondary">
												≈ {new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(p.monthlyRef)}{" "}
												/ month
												{p.discountPercent ? ` (Save ${p.discountPercent}%)` : ""}
											</Typography>
										)}
									</Stack>
									<Divider />
									<Stack spacing={1} sx={{ flexGrow: 1 }}>
										{p.features.slice(0, 6).map((f) => {
											const clean = f.replace(/ \*$/, "");
											return (
												<Tooltip key={f} title={FEATURE_DETAILS?.[clean] || ""} placement="right" arrow>
													<Typography variant="body2">• {f}</Typography>
												</Tooltip>
											);
										})}
										{p.features.length > 6 && (
											<Typography variant="caption" color="text.secondary">
												+ {p.features.length - 6} more
											</Typography>
										)}
									</Stack>
									<Box>
										<Button
											fullWidth
											variant={p.recommended ? "contained" : "outlined"}
											onClick={() => startCheckout(p.id)}
											disabled={checkingOut === p.id}
										>
											{checkingOut === p.id ? <CircularProgress size={18} /> : `Get ${p.name}`}
										</Button>
									</Box>
								</Box>
							</Grid>
						);
					})}
				</Grid>
				{error && (
					<Typography variant="body2" color="error" sx={{ textAlign: "center" }}>
						{error}
					</Typography>
				)}
				{/* Simple feature comparison block */}
				<Stack spacing={3} sx={{ pt: 4 }}>
					<Typography variant="h5" sx={{ textAlign: "center", fontWeight: 600 }}>
						Compare features
					</Typography>
					<Box sx={{ overflowX: "auto" }}>
						<Box component="table" sx={{ width: "100%", borderCollapse: "collapse", minWidth: 720 }}>
							<thead>
								<tr>
									<th style={{ textAlign: "left", padding: "8px 12px" }}>Feature</th>
									{plans.map((p) => (
										<th key={p.id} style={{ textAlign: "center", padding: "8px 12px" }}>
											{p.name}
										</th>
									))}
								</tr>
							</thead>
							<tbody>
								{buildFeatureMatrix(plans).map((row) => (
									<tr key={row.name} style={{ borderTop: "1px solid var(--mui-palette-divider)" }}>
										<td style={{ padding: "8px 12px" }}>
											<Typography variant="body2" sx={{ fontWeight: 500 }}>
												{row.name}
											</Typography>
										</td>
										{plans.map((p) => (
											<td key={p.id} style={{ textAlign: "center", padding: "8px 12px" }}>
												<Typography variant="caption" color={row.map[p.id] ? "success.main" : "text.secondary"}>
													{row.map[p.id] ? "Yes" : "—"}
												</Typography>
											</td>
										))}
									</tr>
								))}
							</tbody>
						</Box>
					</Box>
				</Stack>
			</Stack>
		</Box>
	);
}

// Very small heuristic feature matrix: uses first N common features across plan feature arrays.
function buildFeatureMatrix(plans: PlanDescriptor[]) {
	const all = new Set<string>();
	for (const p of plans) {
		for (const f of p.features) all.add(f);
	}
	const subset = [...all].slice(0, 8);
	return subset.map((name) => ({
		name,
		map: Object.fromEntries(plans.map((p) => [p.id, p.features.includes(name)])),
	}));
}
