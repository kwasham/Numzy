"use client";

import * as React from "react";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import Divider from "@mui/material/Divider";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { CalendarDotsIcon } from "@phosphor-icons/react/dist/ssr/CalendarDots";
import { ChartLineUpIcon } from "@phosphor-icons/react/dist/ssr/ChartLineUp";
import { CurrencyDollarIcon } from "@phosphor-icons/react/dist/ssr/CurrencyDollar";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { SPENDING_TREND_SEED } from "@/data/spending-trend-seed";
import { NoSsr } from "@/components/core/no-ssr";

export type SpendingPoint = {
	month: string;
	spent: number;
	budget?: number;
};

export type SpendingTrendChartProps = {
	data?: SpendingPoint[];
	revalidateLabel?: string;
};

type TrendLine = {
	name: string;
	dataKey: keyof SpendingPoint;
	color: string;
	strokeDasharray: string;
};

const FALLBACK_DATA: SpendingPoint[] = SPENDING_TREND_SEED.map(({ label, spent, budget }) => ({
	month: label,
	spent,
	budget,
}));

const lines: TrendLine[] = [
	{ name: "Spend", dataKey: "spent", color: "var(--mui-palette-primary-main)", strokeDasharray: "0" },
	{ name: "Budget", dataKey: "budget", color: "var(--mui-palette-warning-main)", strokeDasharray: "4 4" },
];

export function SpendingTrendChart({ data = FALLBACK_DATA, revalidateLabel }: SpendingTrendChartProps) {
	const resolved = React.useMemo(() => {
		if (!Array.isArray(data) || data.length === 0) {
			return FALLBACK_DATA;
		}
		return data.map((point) => ({ ...point, budget: point.budget ?? FALLBACK_DATA.at(-1)?.budget ?? 0 }));
	}, [data]);

	const latest = resolved.at(-1);
	const maxValue = React.useMemo(() => {
		return resolved.reduce((acc, point) => Math.max(acc, point.spent, point.budget ?? 0), 0) || 1;
	}, [resolved]);
	const meanSpend = React.useMemo(() => {
		if (resolved.length === 0) return 0;
		return resolved.reduce((acc, point) => acc + point.spent, 0) / resolved.length;
	}, [resolved]);
	const trendDelta = React.useMemo(() => {
		if (resolved.length < 2) return 0;
		const prev = resolved.at(-2)?.spent ?? 0;
		return latest ? latest.spent - prev : 0;
	}, [resolved, latest]);

	const currencyFormatter = React.useMemo(
		() => new Intl.NumberFormat(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 }),
		[]
	);
	const percentage = latest && latest.budget ? Math.min(100, Math.round((latest.spent / latest.budget) * 100)) : 0;

	const chartHeight = 320;

	return (
		<Card variant="outlined" sx={{ height: "100%" }}>
			<CardHeader
				subheader={revalidateLabel}
				title="Spending Over Time"
				titleTypographyProps={{ variant: "subtitle1" }}
			/>
			<CardContent>
				<Stack divider={<Divider />} spacing={3}>
					<Stack
						direction={{ xs: "column", md: "row" }}
						divider={<Divider flexItem orientation="vertical" sx={{ borderBottomWidth: { xs: "1px", md: 0 } }} />}
						spacing={3}
						sx={{ justifyContent: "space-between" }}
					>
						<Summary
							icon={CalendarDotsIcon}
							title="Latest month"
							value={latest ? currencyFormatter.format(latest.spent) : "—"}
						/>
						<Summary icon={CurrencyDollarIcon} title="Monthly average" value={currencyFormatter.format(meanSpend)} />
						<Summary
							icon={ChartLineUpIcon}
							title={trendDelta >= 0 ? "Mom increase" : "Mom decrease"}
							value={currencyFormatter.format(Math.abs(trendDelta))}
						/>
					</Stack>
					<NoSsr fallback={<Box sx={{ height: `${chartHeight}px` }} />}>
						<ResponsiveContainer height={chartHeight} width="100%">
							<LineChart data={resolved} margin={{ top: 0, right: 24, bottom: 0, left: 8 }}>
								<CartesianGrid strokeDasharray="2 4" vertical={false} />
								<XAxis axisLine={false} dataKey="month" tickLine={false} />
								<YAxis axisLine={false} domain={[0, Math.ceil(maxValue / 100) * 100]} hide tickLine={false} />
								{lines.map((line) => (
									<Line
										animationDuration={300}
										dataKey={line.dataKey}
										dot={<Dot />}
										isAnimationActive
										key={line.name}
										name={line.name}
										type="monotone"
										stroke={line.color}
										strokeDasharray={line.strokeDasharray}
										strokeWidth={2}
									/>
								))}
								<Tooltip
									animationDuration={120}
									content={<TooltipContent formatter={currencyFormatter} />}
									cursor={false}
								/>
							</LineChart>
						</ResponsiveContainer>
					</NoSsr>
					<Legend lines={lines} />
					<Box sx={{ display: "flex", alignItems: "center", gap: 2, justifyContent: "space-between" }}>
						<Typography color="text.secondary" variant="body2">
							Latest month budget usage
						</Typography>
						<Box sx={{ flex: 1 }}>
							<LinearProgress value={percentage} variant="determinate" sx={{ height: 8, borderRadius: 4 }} />
						</Box>
						<Typography color="text.secondary" variant="caption">
							{percentage}%
						</Typography>
					</Box>
				</Stack>
			</CardContent>
		</Card>
	);
}

type SummaryProps = {
	icon: React.ElementType;
	title: string;
	value: string;
};

function Summary({ icon: Icon, title, value }: SummaryProps) {
	return (
		<Stack direction="row" spacing={3} sx={{ alignItems: "center" }}>
			<Avatar
				sx={{
					"--Avatar-size": "54px",
					"--Icon-fontSize": "var(--icon-fontSize-lg)",
					bgcolor: "var(--mui-palette-background-paper)",
					boxShadow: "var(--mui-shadows-8)",
					color: "var(--mui-palette-text-primary)",
				}}
			>
				<Icon fontSize="var(--Icon-fontSize)" />
			</Avatar>
			<div>
				<Typography color="text.secondary" variant="overline">
					{title}
				</Typography>
				<Typography variant="h6">{value}</Typography>
			</div>
		</Stack>
	);
}

type DotProps = {
	active?: boolean;
	cx?: number;
	cy?: number;
	stroke?: string;
};

function Dot({ active, cx, cy, stroke }: DotProps) {
	if (!active || typeof cx !== "number" || typeof cy !== "number") {
		return null;
	}

	return <circle cx={cx} cy={cy} fill={stroke} r={4} />;
}

function Legend({ lines }: { lines: TrendLine[] }) {
	return (
		<Stack direction="row" spacing={2}>
			{lines.map((line) => (
				<Stack direction="row" key={line.name} spacing={1} sx={{ alignItems: "center" }}>
					<Box sx={{ bgcolor: line.color, borderRadius: "2px", height: "4px", width: "16px" }} />
					<Typography color="text.secondary" variant="caption">
						{line.name}
					</Typography>
				</Stack>
			))}
		</Stack>
	);
}

type TooltipContentProps = {
	active?: boolean;
	payload?: Array<{ name: string; value: number; stroke: string }>;
	formatter: Intl.NumberFormat;
};

function TooltipContent({ active, payload, formatter }: TooltipContentProps) {
	if (!active || !payload) {
		return null;
	}

	return (
		<Paper sx={{ border: "1px solid var(--mui-palette-divider)", boxShadow: "var(--mui-shadows-16)", p: 1 }}>
			<Stack spacing={1.5}>
				{payload
					.filter((entry) => typeof entry.value === "number")
					.map((entry) => (
						<Stack direction="row" key={entry.name} spacing={1.5} sx={{ alignItems: "center" }}>
							<Stack direction="row" spacing={1} sx={{ alignItems: "center", flex: "1 1 auto" }}>
								<Box sx={{ bgcolor: entry.stroke, borderRadius: "2px", height: "6px", width: "12px" }} />
								<Typography variant="body2">{entry.name}</Typography>
							</Stack>
							<Typography color="text.secondary" variant="body2">
								{formatter.format(entry.value)}
							</Typography>
						</Stack>
					))}
			</Stack>
		</Paper>
	);
}
