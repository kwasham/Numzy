import * as React from "react";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

export type BudgetProgressCategory = {
	name: string;
	spent: number;
	budget: number;
	color?: string;
};

export type BudgetProgressCardProps = {
	categories?: BudgetProgressCategory[];
	currency?: string;
};

const FALLBACK_CATEGORIES: BudgetProgressCategory[] = [
	{ name: "Software", spent: 1800, budget: 2200 },
	{ name: "Infrastructure", spent: 1400, budget: 1800 },
	{ name: "Operations", spent: 900, budget: 1200 },
];

export function BudgetProgressCard({ categories, currency = "USD" }: BudgetProgressCardProps) {
	const resolvedCategories = React.useMemo(() => {
		if (Array.isArray(categories) && categories.length > 0) {
			return categories;
		}
		return FALLBACK_CATEGORIES;
	}, [categories]);

	const formatter = React.useMemo(() => new Intl.NumberFormat(undefined, { style: "currency", currency }), [currency]);

	return (
		<Card variant="outlined" sx={{ height: "100%" }}>
			<CardHeader title="Budget Progress" titleTypographyProps={{ variant: "subtitle1" }} />
			<CardContent>
				<Stack component="ul" spacing={2} sx={{ listStyle: "none", m: 0, p: 0 }}>
					{resolvedCategories.map((category) => {
						const clampedBudget = category.budget > 0 ? category.budget : 1;
						const progress = Math.min(100, Math.max(0, (category.spent / clampedBudget) * 100));
						return (
							<Box component="li" key={category.name} sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
								<Stack
									direction={{ xs: "column", sm: "row" }}
									spacing={1}
									sx={{ alignItems: { sm: "center" }, justifyContent: "space-between" }}
								>
									<Typography fontWeight={600} variant="body2">
										{category.name}
									</Typography>
									<Typography color="text.secondary" sx={{ textAlign: { xs: "left", sm: "right" } }} variant="caption">
										{formatter.format(category.spent)} / {formatter.format(category.budget)}
									</Typography>
								</Stack>
								<LinearProgress
									color={category.color ? undefined : "primary"}
									sx={{
										borderRadius: 1,
										[`& .MuiLinearProgress-bar`]: category.color ? { backgroundColor: category.color } : undefined,
									}}
									value={progress}
									variant="determinate"
								/>
							</Box>
						);
					})}
				</Stack>
			</CardContent>
		</Card>
	);
}
