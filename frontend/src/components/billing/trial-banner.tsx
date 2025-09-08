"use client";

import { useRouter } from "next/navigation";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { useBillingStatus } from "@/hooks/use-billing-status";

interface Props {
	ctaVariant?: "button" | "link";
	hideIfInactive?: boolean;
}

export function TrialBanner({ ctaVariant = "button", hideIfInactive = true }: Props) {
	const { status, loading } = useBillingStatus();
	const router = useRouter();
	const trial = status?.trial;
	if (!loading && hideIfInactive && !trial?.active) return null;

	const daysRemaining = trial?.days_remaining ?? 0;
	// Example assumption: 14-day trial (backend constant). Adjust if backend returns length later.
	const assumedLength = 14;
	const progress = Math.min(100, Math.max(0, ((assumedLength - daysRemaining) / assumedLength) * 100));

	return (
		<Alert
			severity={daysRemaining <= 2 ? "warning" : "info"}
			icon={false}
			sx={{ border: "1px solid", borderColor: "divider", bgcolor: "background.paper" }}
		>
			<Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ alignItems: { sm: "center" } }}>
				<Box sx={{ flex: 1 }}>
					<Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
						{loading
							? "Checking trial status..."
							: trial?.active
								? daysRemaining > 0
									? `Your trial ends in ${daysRemaining} day${daysRemaining === 1 ? "" : "s"}.`
									: "Your trial ends soon."
								: "Trial inactive"}
					</Typography>
					{trial?.active && (
						<Typography variant="body2" color="text.secondary">
							Explore all features. Upgrade now to avoid any interruption when the trial ends.
						</Typography>
					)}
					{trial?.active && (
						<LinearProgress
							variant="determinate"
							value={progress}
							sx={{ mt: 1, height: 6, borderRadius: 3, bgcolor: "background.level1" }}
						/>
					)}
				</Box>
				{trial?.active &&
					(ctaVariant === "button" ? (
						<Button
							variant="contained"
							color={daysRemaining <= 2 ? "warning" : "primary"}
							onClick={() => router.push("/pricing?upgrade=1")}
						>
							Upgrade now
						</Button>
					) : (
						<Button variant="text" onClick={() => router.push("/pricing?upgrade=1")}>
							Upgrade
						</Button>
					))}
			</Stack>
		</Alert>
	);
}
