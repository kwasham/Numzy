import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import Grid from "@mui/material/Grid";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

type MonthlySpendingCardProps = {
	totalExpense: number;
	budget: number;
	currency?: string;
};

// Displays monthly spending progress against a budget target.
export function MonthlySpendingCard({ totalExpense, budget, currency = "USD" }: MonthlySpendingCardProps) {
	const safeBudget = Math.max(1, budget);
	const usagePercent = Math.min(Math.round((totalExpense / safeBudget) * 100), 100);

	return (
		<Card variant="outlined">
			<CardHeader title="Monthly Spending" titleTypographyProps={{ variant: "subtitle1" }} />
			<CardContent>
				<Grid container spacing={3} alignItems="center">
					<Grid item xs={12} md={6}>
						<Stack spacing={1}>
							<Typography color="text.secondary" variant="subtitle2">
								Total expense
							</Typography>
							<Typography variant="h4">
								{totalExpense.toLocaleString(undefined, { style: "currency", currency })}
							</Typography>
							<Typography color="text.secondary" variant="body2">
								Budget: {safeBudget.toLocaleString(undefined, { style: "currency", currency })}
							</Typography>
						</Stack>
					</Grid>
					<Grid item xs={12} md={6}>
						<Stack spacing={1.5}>
							<Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
								<Typography color="text.secondary" variant="subtitle2">
									Budget usage
								</Typography>
								<Typography variant="subtitle2">{usagePercent}%</Typography>
							</Box>
							<LinearProgress value={usagePercent} variant="determinate" sx={{ height: 10, borderRadius: 5 }} />
						</Stack>
					</Grid>
				</Grid>
			</CardContent>
		</Card>
	);
}
