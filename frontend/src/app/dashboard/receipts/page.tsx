import React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { PlusIcon } from "@phosphor-icons/react/dist/ssr/Plus";

import { appConfig } from "@/config/app";
import { ReceiptsContent } from "@/components/dashboard/receipts/receipts-content";

// Filters and view toggle are rendered inside ReceiptsContent to mirror the invoices layout

export const metadata = { title: `List | Receipts | Dashboard | ${appConfig.name}` };

export default async function Page({
	searchParams,
}: {
	searchParams: Promise<Record<string, string | undefined>> | Record<string, string | undefined>;
}) {
	const isPromise = typeof searchParams === "object" && searchParams !== null && "then" in (searchParams as object);
	const sp: Record<string, string | undefined> = isPromise
		? (await (searchParams as Promise<Record<string, string | undefined>>)) || {}
		: (searchParams as Record<string, string | undefined>) || {};
	const {
		merchant,
		endDate,
		id,
		sortDir,
		startDate,
		status,
		category,
		subcategory,
		view = "group",
	} = sp as Record<string, string | undefined>;

	const filters = { merchant, endDate, id, startDate, status, category, subcategory };

	return (
		<Box
			sx={{
				maxWidth: "var(--Content-maxWidth)",
				m: "var(--Content-margin)",
				p: "var(--Content-padding)",
				width: "var(--Content-width)",
			}}
		>
			<Stack spacing={4}>
				<Stack direction={{ xs: "column", sm: "row" }} spacing={3} sx={{ alignItems: "flex-start" }}>
					<Box sx={{ flex: "1 1 auto" }}>
						<Typography variant="h4">Receipts</Typography>
					</Box>
					<Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
						<Button startIcon={<PlusIcon />} variant="contained">
							Upload
						</Button>
					</Stack>
				</Stack>
				{/* Content contains stats, toolbar, filters card and list/pagination */}
				<ReceiptsContent filters={filters} sortDir={sortDir === "asc" ? "asc" : "desc"} view={view} />
			</Stack>
		</Box>
	);
}
