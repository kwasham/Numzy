"use client";

import * as React from "react";
import Stack from "@mui/material/Stack";

import { ReceiptsFiltersCard } from "@/components/dashboard/receipts/receipts-filters-card";
import { ReceiptsList } from "@/components/dashboard/receipts/receipts-list";
import { ReceiptsPagination } from "@/components/dashboard/receipts/receipts-pagination";
import { ReceiptsStats } from "@/components/dashboard/receipts/receipts-stats";
import { ReceiptsViewModeButton } from "@/components/dashboard/receipts/view-mode-button";
import { ReceiptUploadWidget } from "@/components/widgets/receipt-upload-widget";

export interface ReceiptsContentProps {
	filters?: {
		id?: string;
		merchant?: string;
		status?: string;
		startDate?: string;
		endDate?: string;
		category?: string;
		subcategory?: string;
	};
	sortDir?: "asc" | "desc";
	view?: string;
}

export function ReceiptsContent({ filters, sortDir = "desc", view: _view }: ReceiptsContentProps) {
	const [count, setCount] = React.useState(0);
	const [page, setPage] = React.useState(0);
	const pageSize = 10;
	const [stats, setStats] = React.useState({
		countAll: 0,
		countCompleted: 0,
		countPending: 0,
		amountAll: 0,
		amountCompleted: 0,
		amountPending: 0,
	});

	return (
		<Stack spacing={4} sx={{ flex: "1 1 auto", minWidth: 0 }}>
			{/* Stats at top spanning the container width via Grid inside */}
			<ReceiptsStats
				totals={{ all: stats.countAll, completed: stats.countCompleted, failed: 0 }}
				amounts={{ all: stats.amountAll, completed: stats.amountCompleted, pending: stats.amountPending }}
			/>
			{/* Toolbar row (match invoice page style) */}
			<Stack direction="row" spacing={2} sx={{ alignItems: "center", justifyContent: "flex-end" }}>
				<ReceiptsViewModeButton view={_view} />
			</Stack>
			{/* Main content row: filters left, list & pagination right */}
			<Stack direction="row" spacing={4} sx={{ alignItems: "flex-start" }}>
				<ReceiptsFiltersCard filters={filters} sortDir={sortDir} view={_view} />
				<Stack spacing={4} sx={{ flex: "1 1 auto", minWidth: 0 }}>
					<ReceiptsList
						filters={filters}
						sortDir={sortDir}
						page={page}
						pageSize={pageSize}
						view={_view}
						onCountChange={setCount}
						onStatsChange={setStats}
					/>
					{_view !== "group" && (
						<ReceiptsPagination count={count} page={page} pageSize={pageSize} onPageChange={setPage} />
					)}
					{/* Upload widget below the table */}
					<ReceiptUploadWidget />
				</Stack>
			</Stack>
		</Stack>
	);
}

export default ReceiptsContent;
