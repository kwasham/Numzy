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

import { availablePlans, PLAN_CAPABILITIES, PlanId } from "../../../../../shared/types/plan";
import { Plan } from "./plan";

export function PlansTable({ catalog = {} }) {
	const [yearly, setYearly] = React.useState(false);
	const hasYearly = availablePlans(catalog || {}, true).some((pid) => !!catalog?.[pid]?.yearly?.price);
	const displayPrice = (pid) => {
		const entry = catalog?.[pid];
		if (!entry) return PLAN_CAPABILITIES[pid].monthlyPrice || 0;
		if (yearly && entry.yearly?.price) return (entry.yearly.price / 12).toFixed(2);
		return (entry.monthly?.price ?? entry.price ?? (PLAN_CAPABILITIES[pid].monthlyPrice || 0)).toFixed(2);
	};
	return (
		<Box sx={{ bgcolor: "var(--mui-palette-background-level1)", py: { xs: "60px", sm: "120px" } }}>
			<Container maxWidth="lg">
				<Stack spacing={3}>
					<Stack spacing={2} sx={{ alignItems: "center" }}>
						<Typography sx={{ textAlign: "center" }} variant="h3">
							Start today. Boost up your services!
						</Typography>
						<Typography color="text.secondary" sx={{ textAlign: "center" }} variant="body1">
							Join 10,000+ developers &amp; designers using Devias to power modern web projects.
						</Typography>
						{hasYearly && (
							<Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
								<Switch checked={yearly} onChange={() => setYearly((p) => !p)} />
								<Typography variant="body1">Billed annually</Typography>
								<Chip color="success" label="Save" size="small" />
							</Stack>
						)}
					</Stack>
					<div>
						<Grid container spacing={3}>
							<Grid
								size={{
									md: 4,
									xs: 12,
								}}
							>
								{availablePlans(catalog || {}, true).map((pid) => {
									const cap = PLAN_CAPABILITIES[pid];
									const features = [
										`${cap.monthlyQuota} monthly quota`,
										`Retention: ${cap.retentionDays === "custom" ? "Custom" : cap.retentionDays + "d"}`,
										cap.prioritySupport ? "Priority support" : "Community support",
										cap.advancedAnalytics ? "Advanced analytics" : "Basic analytics",
										cap.sso ? "SSO/SAML" : "—",
									].filter(Boolean);
									return (
										<Grid key={pid} size={{ md: 3, xs: 12 }}>
											<Plan
												action={
													<Button variant={pid === PlanId.PERSONAL || pid === PlanId.PRO ? "contained" : "outlined"}>
														{pid === PlanId.BUSINESS ? "Contact us" : "Select"}
													</Button>
												}
												currency="USD"
												description={cap.name + " tier"}
												features={features}
												id={pid}
												name={cap.name}
												price={Number.parseFloat(displayPrice(pid))}
											/>
										</Grid>
									);
								})}
							</Grid>
						</Grid>
					</div>
					<div>
						<Typography color="text.secondary" component="p" sx={{ textAlign: "center" }} variant="caption">
							30% of our income goes into Whale Charity
						</Typography>
					</div>
				</Stack>
			</Container>
		</Box>
	);
}
