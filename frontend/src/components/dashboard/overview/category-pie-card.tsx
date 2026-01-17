"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { Cell, Pie, PieChart, Tooltip } from "recharts";

import { NoSsr } from "@/components/core/no-ssr";

type ExpenseCategory = {
	name: string;
	value: number;
	color?: string;
};

type CategoryPieCardProps = {
	/**
	 * Optional precomputed categories. When omitted, this card will fetch
	 * the current breakdown from the backend metrics endpoint on the client.
	 */
	categories?: ExpenseCategory[] | null;
	totalLabel?: string;
};

export const CATEGORY_COLORS = ["#2563eb", "#22c55e", "#f97316", "#ec4899", "#a855f7", "#14b8a6"] as const;

// Presents category spend distribution in a responsive card with a client-side pie chart.
export function CategoryPieCard({ categories, totalLabel = "Total" }: CategoryPieCardProps) {
	// Optional client-side fetch of real data when categories aren't provided.
	const [fetched, setFetched] = React.useState<ExpenseCategory[] | null>(null);
	const [loading, setLoading] = React.useState<boolean>(false);
	React.useEffect(() => {
		if (categories && categories.length > 0) return; // external data provided
		let didCancel = false;
		const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
		const ctrl = new AbortController();
		const timer = setTimeout(() => ctrl.abort(), 2500);
		setLoading(true);
		fetch(`${API_BASE}/metrics/spend/categories`, { cache: "no-store", signal: ctrl.signal })
			.then(async (res) => {
				if (!res.ok) throw new Error(String(res.status));
				const json = await res.json();
				const items: ExpenseCategory[] = Array.isArray(json?.items)
					? json.items
							.map((it: any, idx: number) => ({
								name: typeof it?.name === "string" && it.name.trim() ? it.name.trim() : "Uncategorized",
								value: Number(it?.amount ?? it?.total ?? 0) || 0,
								color: CATEGORY_COLORS[idx % CATEGORY_COLORS.length],
							}))
							.filter((it: ExpenseCategory) => Number.isFinite(it.value) && it.value > 0)
					: [];
				if (!didCancel) setFetched(items);
			})
			.catch(() => {
				if (!didCancel) setFetched([]);
			})
			.finally(() => {
				if (!didCancel) setLoading(false);
				clearTimeout(timer);
			});
		return () => {
			didCancel = true;
			ctrl.abort();
			clearTimeout(timer);
		};
	}, [categories]);

	const effective = categories && categories.length > 0 ? categories : fetched || [];

	const total = React.useMemo(
		() => effective.reduce((acc, cat) => (Number.isFinite(cat.value) ? acc + Math.max(0, cat.value) : acc), 0),
		[effective]
	);
	const currencyFormatter = React.useMemo(
		() => new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }),
		[]
	);
	const chartData = React.useMemo(
		() =>
			effective.map((category, index) => ({
				name: category.name,
				value: Math.max(0, category.value),
				color: category.color ?? CATEGORY_COLORS[index % CATEGORY_COLORS.length],
			})),
		[effective]
	);
	const chartSize = 220;
	const chartThickness = 36;

	return (
		<Card variant="outlined" sx={{ height: "100%" }}>
			<CardHeader title="Spending by Category" titleTypographyProps={{ variant: "subtitle1" }} />
			<CardContent>
				<Stack spacing={3} sx={{ height: "100%" }}>
					<Box sx={{ alignItems: "center", display: "flex", justifyContent: "center" }}>
						<Box sx={{ height: chartSize, width: chartSize }}>
							<NoSsr fallback={<Box sx={{ height: "100%", width: "100%" }} />}>
								{loading ? (
									<Box sx={{ height: chartSize, width: chartSize }} />
								) : chartData.length > 0 ? (
									<PieChart height={chartSize} margin={{ top: 0, right: 0, bottom: 0, left: 0 }} width={chartSize}>
										<Pie
											animationDuration={300}
											cx={chartSize / 2}
											cy={chartSize / 2}
											data={chartData}
											dataKey="value"
											innerRadius={chartSize / 2 - chartThickness}
											nameKey="name"
											outerRadius={chartSize / 2}
											strokeWidth={0}
										>
											{chartData.map((entry) => (
												<Cell fill={entry.color} key={entry.name} />
											))}
										</Pie>
										<Tooltip
											animationDuration={120}
											cursor={{ fill: "rgba(148, 163, 184, 0.12)" }}
											formatter={(value: number | string) =>
												currencyFormatter.format(typeof value === "number" ? value : Number(value ?? 0))
											}
										/>
									</PieChart>
								) : (
									<Box
										sx={{
											display: "flex",
											alignItems: "center",
											justifyContent: "center",
											height: "100%",
											color: "text.secondary",
										}}
									>
										<Typography variant="body2">No category data</Typography>
									</Box>
								)}
							</NoSsr>
						</Box>
					</Box>
					<Stack spacing={0.5}>
						<Typography color="text.secondary" variant="subtitle2">
							{totalLabel}
						</Typography>
						<Typography variant="h4">{currencyFormatter.format(total)}</Typography>
					</Stack>
					<Box
						sx={{
							display: "grid",
							gap: 2,
							gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
						}}
					>
						{chartData.map((category) => {
							const percentage = total > 0 ? Math.round((category.value / total) * 100) : 0;
							return (
								<Stack key={category.name} spacing={0.5} sx={{ alignItems: "flex-start" }}>
									<Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
										<Box sx={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: category.color }} />
										<Typography variant="body2">{category.name}</Typography>
									</Stack>
									<Typography variant="subtitle1">{currencyFormatter.format(category.value)}</Typography>
									<Typography color="text.secondary" variant="caption">
										{percentage}%
									</Typography>
								</Stack>
							);
						})}
					</Box>
				</Stack>
			</CardContent>
		</Card>
	);
}
