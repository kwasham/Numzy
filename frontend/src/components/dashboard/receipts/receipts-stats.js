"use client";
import * as React from "react";
import Avatar from "@mui/material/Avatar";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { CheckIcon } from "@phosphor-icons/react/dist/ssr/Check";
import { ClockIcon } from "@phosphor-icons/react/dist/ssr/Clock";
import { ReceiptIcon } from "@phosphor-icons/react/dist/ssr/Receipt";

export function ReceiptsStats({
	totals = { all: 0, completed: 0, failed: 0 },
	amounts = { all: 0, completed: 0, pending: 0 },
}) {
	const countAll = Number(totals?.all ?? 0);
	const countCompleted = Number(totals?.completed ?? 0);
	const countFailed = Number(totals?.failed ?? 0);
	const countPending = Math.max(0, countAll - countCompleted - countFailed);

	const amountAll = Number(amounts?.all ?? 0);
	const amountCompleted = Number(amounts?.completed ?? 0);
	const amountPending = Number(amounts?.pending ?? 0);

	const fmtCurrency = (n) =>
		new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(
			Number.isFinite(n) ? n : 0
		);

	return (
		<Grid container spacing={4}>
			<Grid
				size={{
					md: 6,
					xl: 4,
					xs: 12,
				}}
			>
				<Card>
					<CardContent>
						<Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
							<Avatar
								sx={{
									"--Avatar-size": "48px",
									bgcolor: "var(--mui-palette-background-paper)",
									boxShadow: "var(--mui-shadows-8)",
									color: "var(--mui-palette-text-primary)",
								}}
							>
								<ReceiptIcon fontSize="var(--icon-fontSize-lg)" />
							</Avatar>
							<div>
								<Typography color="text.secondary" variant="body2">
									Total
								</Typography>
								<Typography variant="h6">{fmtCurrency(amountAll)}</Typography>
								<Typography color="text.secondary" variant="body2">
									from {new Intl.NumberFormat("en-US").format(countAll)} receipts
								</Typography>
							</div>
						</Stack>
					</CardContent>
				</Card>
			</Grid>
			<Grid
				size={{
					md: 6,
					xl: 4,
					xs: 12,
				}}
			>
				<Card>
					<CardContent>
						<Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
							<Avatar
								sx={{
									"--Avatar-size": "48px",
									bgcolor: "var(--mui-palette-background-paper)",
									boxShadow: "var(--mui-shadows-8)",
									color: "var(--mui-palette-text-primary)",
								}}
							>
								<CheckIcon fontSize="var(--icon-fontSize-lg)" />
							</Avatar>
							<div>
								<Typography color="text.secondary" variant="body2">
									Completed
								</Typography>
								<Typography variant="h6">{fmtCurrency(amountCompleted)}</Typography>
								<Typography color="text.secondary" variant="body2">
									from {new Intl.NumberFormat("en-US").format(countCompleted)} receipts
								</Typography>
							</div>
						</Stack>
					</CardContent>
				</Card>
			</Grid>
			<Grid
				size={{
					md: 6,
					xl: 4,
					xs: 12,
				}}
			>
				<Card>
					<CardContent>
						<Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
							<Avatar
								sx={{
									"--Avatar-size": "48px",
									bgcolor: "var(--mui-palette-background-paper)",
									boxShadow: "var(--mui-shadows-8)",
									color: "var(--mui-palette-text-primary)",
								}}
							>
								<ClockIcon fontSize="var(--icon-fontSize-lg)" />
							</Avatar>
							<div>
								<Typography color="text.secondary" variant="body2">
									Pending
								</Typography>
								<Typography variant="h6">{fmtCurrency(amountPending)}</Typography>
								<Typography color="text.secondary" variant="body2">
									from {new Intl.NumberFormat("en-US").format(countPending)} receipts
								</Typography>
							</div>
						</Stack>
					</CardContent>
				</Card>
			</Grid>
		</Grid>
	);
}
