"use client";
import * as React from "react";
import Avatar from "@mui/material/Avatar";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { TagIcon } from "@phosphor-icons/react/dist/ssr/Tag";

export function ReceiptsStats({
	_totals = { all: 0, completed: 0, failed: 0 },
	_amounts = { all: 0, completed: 0, pending: 0 },
	categories = [], // Array<{ category, amount, count }>
}) {
	const fmtCurrency = (n) =>
		new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(
			Number.isFinite(n) ? n : 0
		);

	// Normalize incoming categories and fold into the five canonical buckets
	const CANONICAL = [
		{ key: "Cost of Goods Sold", label: "Cost of Goods Sold" },
		{ key: "Operational Expenses", label: "Operational Expenses" },
		{ key: "Travel Expenses", label: "Travel Expenses", aliases: ["Travel Specific Expenses"] },
		{ key: "Meals and Entertainment", label: "Meals and Entertainment" },
		{ key: "Other", label: "Other" },
	];

	const aliasMap = new Map();
	for (const c of CANONICAL) {
		aliasMap.set(c.key.toLowerCase(), c.key);
		if (c.aliases) for (const a of c.aliases) aliasMap.set(String(a).toLowerCase(), c.key);
	}

	const sums = new Map(CANONICAL.map((c) => [c.key, { amount: 0, count: 0 }]));
	for (const item of Array.isArray(categories) ? categories : []) {
		const name = String(item?.category ?? "Other").toLowerCase();
		const key = aliasMap.get(name) || (name.includes("travel") ? "Travel Expenses" : aliasMap.get(name) || undefined);
		const bucket = key && sums.has(key) ? key : "Other";
		const cur = sums.get(bucket);
		cur.amount += Number(item?.amount ?? 0);
		cur.count += Number(item?.count ?? 0);
		sums.set(bucket, cur);
	}

	const nf = new Intl.NumberFormat("en-US");

	return (
		<Grid container spacing={4}>
			{CANONICAL.map((c) => {
				const v = sums.get(c.key) || { amount: 0, count: 0 };
				return (
					<Grid key={c.key} size={{ md: 6, xl: 4, xs: 12 }}>
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
										<TagIcon fontSize="var(--icon-fontSize-lg)" />
									</Avatar>
									<div>
										<Typography color="text.secondary" variant="body2">
											{c.label}
										</Typography>
										<Typography variant="h6">{fmtCurrency(Number(v.amount))}</Typography>
										<Typography color="text.secondary" variant="body2">
											from {nf.format(Number(v.count || 0))} receipts
										</Typography>
									</div>
								</Stack>
							</CardContent>
						</Card>
					</Grid>
				);
			})}
		</Grid>
	);
}
