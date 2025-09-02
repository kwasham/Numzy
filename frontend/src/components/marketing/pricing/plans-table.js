"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Container from "@mui/material/Container";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";

import { BillingButtons } from "@/components/billing/billing-buttons";

import { Plan } from "./plan";
import { generatePlanFeatures, PLAN_METADATA, PLAN_ORDER, planPrice, priceMeta, RAW_PRICING } from "./pricing-config";

// Lazy Sentry import (avoid SSR issues)
// Lightweight Sentry shim (frontend instrumentation) - avoids dynamic import lint noise
const sentry = (typeof globalThis !== "undefined" && (globalThis.Sentry || globalThis.__SENTRY__)) || null;

export function PlansTable() {
	// Determine if any paid plan exposes a discount to enable yearly toggle
	const discountEligible = React.useMemo(
		() =>
			PLAN_ORDER.some((id) => {
				const meta = priceMeta(id);
				return meta.discountPercent && meta.discountPercent > 0 && meta.monthly > 0;
			}),
		[]
	);
	const [yearly, setYearly] = React.useState(false);
	const [selectedPlan, setSelectedPlan] = React.useState(null);

	// restore persisted selection
	React.useEffect(() => {
		try {
			const stored = globalThis?.localStorage?.getItem("pricing:selectedPlan");
			if (stored && PLAN_ORDER.includes(stored)) {
				setSelectedPlan(stored);
			}
		} catch {
			/* ignore */
		}
	}, []);
	// Hide custom priced tiers (monthly 0) except free
	// Build list of plan ids to display. We intentionally hide the free plan card
	// (still keeping its metadata for internal use / upgrade flows) and any
	// custom-priced tiers with monthly === 0.
	const ids = React.useMemo(
		() =>
			PLAN_ORDER.filter((id) => {
				if (id === "free") return false; // hide free tier card
				const p = RAW_PRICING[id];
				return p && p.monthly > 0;
			}),
		[]
	);
	// Monthly vs. yearly (displayed as discounted monthly equivalent) pricing
	const periodLabel = yearly ? "/year" : "/month";
	const currency = "USD";
	const structuredOffers = ids.map((id) => {
		const meta = priceMeta(id);
		return {
			"@type": "Offer",
			priceCurrency: currency,
			price: meta.monthly,
			name: PLAN_METADATA[id].name,
			description: PLAN_METADATA[id].description,
			category: "software",
		};
	});

	// Debounced impression tracking: dispatch impressions after short delay to avoid spamming.
	React.useEffect(() => {
		const cards = document.querySelectorAll('[data-pricing-card="true"]');
		if (!("IntersectionObserver" in globalThis)) return;
		const pending = new Map(); // element -> timeout id
		const observer = new IntersectionObserver(
			(entries) => {
				for (const e of entries) {
					if (e.isIntersecting && !pending.has(e.target)) {
						const plan = e.target.dataset.plan;
						const tid = setTimeout(() => {
							globalThis.dispatchEvent(new CustomEvent("pricing:impression", { detail: { plan } }));
							observer.unobserve(e.target);
							pending.delete(e.target);
						}, 60); // 60ms debounce window
						pending.set(e.target, tid);
					}
				}
			},
			{ threshold: 0.4 }
		);
		for (const c of cards) observer.observe(c);
		return () => {
			observer.disconnect();
			for (const tid of pending.values()) clearTimeout(tid);
			pending.clear();
		};
	}, []);

	// feature delta map
	const accumulated = new Set();
	const featureDeltaMap = ids.reduce((acc, id) => {
		// dynamically generate features (quota pluralization etc.)
		const feats = generatePlanFeatures(id);
		acc[id] = feats.map((f) => ({ name: f, isNew: !accumulated.has(f) && f !== "—" }));
		for (const f of feats) accumulated.add(f);
		return acc;
	}, {});

	return (
		<Box sx={{ bgcolor: "var(--mui-palette-background-level1)", py: { xs: "60px", sm: "120px" } }}>
			<Container maxWidth={false} sx={{ maxWidth: 1680, mx: "auto", px: { xs: 2, md: 3 } }}>
				<Stack spacing={3}>
					<Stack spacing={2} sx={{ alignItems: "center" }}>
						<Typography sx={{ textAlign: "center" }} variant="h3">
							Start today. Boost up your services!
						</Typography>
						<Typography color="text.secondary" sx={{ textAlign: "center" }} variant="body1">
							Join 10,000+ developers &amp; designers using Devias to power modern web projects.
						</Typography>
						<Stack
							direction="row"
							spacing={2}
							sx={{ alignItems: "center", flexWrap: "wrap", justifyContent: "center" }}
						>
							{discountEligible ? (
								<Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
									<Switch
										checked={yearly}
										onChange={() => {
											setYearly((p) => !p);
											try {
												sentry?.captureMessage("pricing.toggle_yearly", { level: "info" });
											} catch {
												// ignore
											}
										}}
										inputProps={{ "aria-label": "Toggle annual billing" }}
									/>
									<Typography variant="body1">Billed annually</Typography>
									{yearly && <Chip color="success" label="Save" size="small" />}
								</Stack>
							) : null}
						</Stack>
					</Stack>
					<div>
						<Grid
							container
							// Use responsive row/column spacing for better visual separation
							rowSpacing={{ xs: 2, md: 4 }}
							columnSpacing={{ xs: 2, md: 4 }}
							wrap="wrap"
							sx={{
								overflowX: { xs: "auto", md: "visible" },
								py: { xs: 1, md: 2 },
								scrollSnapType: { xs: "x mandatory", md: "none" },
								flexWrap: { xs: "nowrap", md: "wrap" }, // keep horizontal scroll on mobile, wrap on desktop
								justifyContent: { xs: "flex-start", md: "center" },
								alignItems: "stretch",
								"& > .MuiGrid-item": {
									scrollSnapAlign: { xs: "start", md: "none" },
									// Ensure a reasonable min width so horizontal scroll feels snappy on mobile
									minWidth: { xs: 260, sm: 300, md: "auto" },
								},
							}}
						>
							{ids.map((id) => {
								const meta = priceMeta(id);
								const isYear = yearly;
								const price = planPrice(id, { yearly: isYear });
								const monthlyRef = isYear ? meta.annualMonthly : undefined;
								const discountPercent = isYear ? meta.discountPercent : undefined;
								const { name, description, recommended } = PLAN_METADATA[id];
								const featureEntries = featureDeltaMap[id];
								// Provide a real checkout action for Pro; keep defaults for others to minimize risk.
								const action = id === "pro" ? <BillingButtons size="large" /> : undefined;
								return (
									<Grid size={{ xs: 12, sm: 6, md: 3 }} key={id} data-pricing-card="true" data-plan={id}>
										<Plan
											currency="USD"
											description={description}
											features={featureEntries.map((f) => (f.isNew ? `${f.name} *` : f.name))}
											id={id}
											name={name}
											price={price}
											period={periodLabel}
											monthlyReference={monthlyRef}
											discountPercent={discountPercent}
											recommended={recommended}
											selected={selectedPlan === id}
											action={action}
											onSelect={(planId) => {
												setSelectedPlan(planId);
												try {
													globalThis?.localStorage?.setItem("pricing:selectedPlan", planId);
												} catch {
													/* ignore */
												}
											}}
										/>
									</Grid>
								);
							})}
						</Grid>
						<Typography color="text.secondary" component="p" sx={{ textAlign: "center", mt: 2 }} variant="caption">
							* denotes feature first introduced at that tier
						</Typography>
					</div>
					<div>
						<Typography color="text.secondary" component="p" sx={{ textAlign: "center" }} variant="caption">
							30% of our income goes into Whale Charity
						</Typography>
						{/* Structured data for SEO */}
						<script
							type="application/ld+json"
							dangerouslySetInnerHTML={{
								__html: JSON.stringify({
									"@context": "https://schema.org",
									"@type": "AggregateOffer",
									priceCurrency: "USD",
									offers: structuredOffers,
								}),
							}}
						/>
					</div>
				</Stack>
			</Container>
		</Box>
	);
}
