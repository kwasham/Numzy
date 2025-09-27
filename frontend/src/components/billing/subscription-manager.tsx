"use client";

import * as React from "react";
import { useAuth } from "@clerk/nextjs";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { BillingStatus, changeSubscriptionPlan, createPortalSession, fetchBillingStatus } from "@/lib/billing-client";

interface Props {
	hidePortal?: boolean;
}

export function SubscriptionManager({ hidePortal }: Props) {
	const { getToken } = useAuth();
	const [status, setStatus] = React.useState<BillingStatus | null>(null);
	const [loading, setLoading] = React.useState(true);
	const [changing, setChanging] = React.useState(false);
	const [error, setError] = React.useState<string | null>(null);
	const [success, setSuccess] = React.useState<string | null>(null);

	const load = React.useCallback(async () => {
		setLoading(true);
		setError(null);
		const st = await fetchBillingStatus(getToken);
		setStatus(st);
		setLoading(false);
	}, [getToken]);
	React.useEffect(() => {
		load();
	}, [load]); // initial

	// Simple derived flags
	const plan = status?.plan || "free";
	const activeSub = (status?.subscription_status || "").toLowerCase() === "active";
	const trialingSub = (status?.subscription_status || "").toLowerCase() === "trialing";
	const trialActive = status?.trial?.active;
	const trialEndsAt = status?.trial?.ends_at;

	async function handleChange(targetPlan: "personal" | "pro" | "business", deferDowngrade = false) {
		setChanging(true);
		setError(null);
		setSuccess(null);
		const res = await changeSubscriptionPlan({ targetPlan, deferDowngrade }, getToken);
		if (res.ok) {
			setSuccess("Subscription change submitted. Refreshing status...");
			for (let i = 0; i < 5; i++) {
				await new Promise((r) => setTimeout(r, 2500));
				await load();
			}
		} else {
			setError(`Change failed (status ${res.status}): ${JSON.stringify(res.body)}`);
		}
		setChanging(false);
	}

	async function handlePortal() {
		setChanging(true);
		setError(null);
		setSuccess(null);
		const url = await createPortalSession(getToken);
		setChanging(false);
		if (url) {
			globalThis.location.href = url;
		} else {
			setError("Could not open billing portal.");
		}
	}

	return (
		<Box sx={{ p: 2, border: "1px solid", borderColor: "divider", borderRadius: 2 }}>
			<Stack spacing={2}>
				<Typography variant="h6">Subscription</Typography>
				{loading && <CircularProgress size={24} />}
				{!loading && status && (
					<Stack spacing={1}>
						<Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
							<Chip
								label={`Plan: ${plan}`}
								size="small"
								color={plan === "pro" ? "primary" : plan === "personal" ? "success" : "default"}
							/>
							{activeSub && <Chip label="Active" size="small" color="success" />}
							{trialingSub && <Chip label="Trialing (Stripe)" size="small" color="info" />}
							{trialActive && !trialingSub && <Chip label="Trial Active" size="small" color="info" />}
							{status.payment_state === "requires_action" && (
								<Chip label="Action required" size="small" color="warning" />
							)}
						</Stack>
						{trialActive && trialEndsAt && (
							<Typography variant="body2" color="text.secondary">
								Trial ends: {new Date(trialEndsAt).toLocaleDateString()}
							</Typography>
						)}
						{status.payment_state === "requires_action" && (
							<Alert severity="warning">Payment action required in Stripe portal.</Alert>
						)}
						{error && (
							<Alert severity="error" onClose={() => setError(null)}>
								{error}
							</Alert>
						)}
						{success && (
							<Alert severity="success" onClose={() => setSuccess(null)}>
								{success}
							</Alert>
						)}
						<Divider />
						<Stack direction={{ xs: "column", sm: "row" }} spacing={1} flexWrap="wrap">
							{/* Upgrade/Downgrade buttons logic */}
							{/* Show upgrade to Personal if free & no active subscription */}
							{plan === "free" && !activeSub && !trialingSub && (
								<Button disabled={changing} variant="contained" onClick={() => handleChange("personal")}>
									Upgrade to Personal
								</Button>
							)}
							{plan === "personal" && (
								<Button disabled={changing} variant="contained" onClick={() => handleChange("pro")}>
									Upgrade to Pro
								</Button>
							)}
							{plan === "pro" && (
								<Button disabled={changing} variant="outlined" onClick={() => handleChange("personal", true)}>
									Schedule downgrade to Personal
								</Button>
							)}
							{plan === "business" && (
								<Button disabled={changing} variant="outlined" onClick={() => handleChange("pro", true)}>
									Schedule downgrade to Pro
								</Button>
							)}
							{!hidePortal && (activeSub || trialingSub) && (
								<Button disabled={changing} variant="text" onClick={handlePortal}>
									Manage billing
								</Button>
							)}
							<Button disabled={changing} variant="text" onClick={load}>
								Refresh
							</Button>
						</Stack>
					</Stack>
				)}
			</Stack>
		</Box>
	);
}
