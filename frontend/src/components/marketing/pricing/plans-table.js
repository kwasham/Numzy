"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Container from "@mui/material/Container";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";

import { Plan } from "./plan";
import { PLAN_FEATURES, PLAN_METADATA, PLAN_ORDER, planPrice, priceMeta } from "./pricing-config";

export function PlansTable() {
	const [yearly, setYearly] = React.useState(false);
	// Monthly vs. yearly (displayed as discounted monthly equivalent) pricing
	const periodLabel = yearly ? "/year" : "/month";
	const ids = PLAN_ORDER;
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

	// impression tracking
	React.useEffect(() => {
		const cards = document.querySelectorAll('[data-pricing-card="true"]');
		if (!("IntersectionObserver" in globalThis)) return;
		const observer = new IntersectionObserver(
			(entries) => {
				for (const e of entries) {
					if (e.isIntersecting) {
						const plan = e.target.dataset.plan;
						globalThis.dispatchEvent(new CustomEvent("pricing:impression", { detail: { plan } }));
						observer.unobserve(e.target);
					}
				}
			},
			{ threshold: 0.4 }
		);
		for (const c of cards) observer.observe(c);
		return () => observer.disconnect();
	}, []);

	// feature delta map
	const accumulated = new Set();
	const featureDeltaMap = ids.reduce((acc, id) => {
		const feats = PLAN_FEATURES[id];
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
							<Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
								<Switch
									checked={yearly}
									onChange={() => setYearly((p) => !p)}
									inputProps={{ "aria-label": "Toggle annual billing" }}
								/>
								<Typography variant="body1">Billed annually</Typography>
								{yearly && <Chip color="success" label="Save" size="small" />}
							</Stack>
						</Stack>
					</Stack>
					<div>
						<Grid
							container
							spacing={2}
							wrap="nowrap"
							sx={{
								overflowX: { xs: "auto", md: "visible" },
								py: 1,
								scrollSnapType: { xs: "x mandatory", md: "none" },
								"& > .MuiGrid-item": { scrollSnapAlign: { xs: "start", md: "none" } },
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
								const actionButton =
									id === "business" ? (
										<Button
											color="secondary"
											variant="contained"
											onClick={() => {
												// analytics placeholder
												globalThis?.dispatchEvent(new CustomEvent("pricing:contact", { detail: { plan: id } }));
												globalThis.location.href = "mailto:sales@example.com?subject=Business%20Plan%20Inquiry";
											}}
										>
											Contact us
										</Button>
									) : (
										<Button
											variant={id === "personal" || id === "pro" ? "contained" : "outlined"}
											onClick={() => {
												globalThis?.dispatchEvent(
													new CustomEvent("pricing:select", { detail: { plan: id, yearly: isYear } })
												);
											}}
										>
											Select
										</Button>
									);
								return (
									<Grid size={{ xs: 12, sm: 6, md: 3 }} key={id} data-pricing-card="true" data-plan={id}>
										<Plan
											action={actionButton}
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
										/>
									</Grid>
								);
							})}
						</Grid>
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
