import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { ReceiptsFilters } from "./receipts-filters";

export function ReceiptsFiltersCard({ filters, sortDir, view }) {
	return (
		<Card
			sx={{ display: { xs: "none", lg: "block" }, flex: "0 0 auto", width: "340px", position: "sticky", top: "80px" }}
		>
			<CardContent>
				<Stack spacing={3}>
					<Typography variant="h5">Filters</Typography>
					<ReceiptsFilters filters={filters} sortDir={sortDir} view={view} />
				</Stack>
			</CardContent>
		</Card>
	);
}
