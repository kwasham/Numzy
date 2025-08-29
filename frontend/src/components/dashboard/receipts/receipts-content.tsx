"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";

import { primePartialReceipt } from "@/components/dashboard/receipts/receipt-cache";
import { ReceiptsFilters } from "@/components/dashboard/receipts/receipts-filters";
import { ReceiptsList } from "@/components/dashboard/receipts/receipts-list";
import { ReceiptsPagination } from "@/components/dashboard/receipts/receipts-pagination";
import { ReceiptsSelectionProvider } from "@/components/dashboard/receipts/receipts-selection-context";
import { ReceiptsStats } from "@/components/dashboard/receipts/receipts-stats";
import { ReceiptsTable } from "@/components/dashboard/receipts/receipts-table";
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
}

export function ReceiptsContent({ filters, sortDir = "desc" }: ReceiptsContentProps) {
	const [count, setCount] = React.useState(0);
	const [page, setPage] = React.useState(0);
	const pageSize = 10;
	const [stats, setStats] = React.useState({
		countAll: 0,
		countCompleted: 0,
		countPending: 0,
		countProcessing: 0,
		countFailed: 0,
		amountAll: 0,
		amountCompleted: 0,
		amountPending: 0,
		categories: [] as Array<{ category: string; amount: number; count: number }>,
	});
	// Row type matches the Receipt shape emitted by ReceiptsList onRowsChange
	type ReceiptRow = {
		id: number;
		filename: string;
		status: string;
		extracted_data?: Record<string, unknown> | null;
		audit_decision?: Record<string, unknown> | null;
		created_at: string;
		updated_at: string;
		extraction_progress: number;
		audit_progress: number;
	};
	const [rows, setRows] = React.useState<ReceiptRow[]>([]);

	// Prime cache whenever rows change (only minimal data)
	React.useEffect(() => {
		for (const r of rows) primePartialReceipt(r);
	}, [rows]);

	return (
		<Stack spacing={4} sx={{ flex: "1 1 auto", minWidth: 0 }}>
			{/* Stats at top (keep) */}
			<ReceiptsStats
				_totals={{ all: stats.countAll, completed: stats.countCompleted, failed: 0 }}
				_amounts={{ all: stats.amountAll, completed: stats.amountCompleted, pending: stats.amountPending }}
				categories={stats.categories}
			/>
			{/* Table Card (Orders style) */}
			<ReceiptsSelectionProvider receipts={rows}>
				<Card>
					{/* Orders-like structure: Filters at top, then table, then pagination */}
					<Box sx={{ p: 2 }}>
						<ReceiptsFilters filters={filters || {}} sortDir={sortDir} statusCounts={stats} />
					</Box>
					<Divider />
					<Box sx={{ overflowX: "auto" }}>
						<ReceiptsTable rows={rows} />
					</Box>
					<Divider />
					<Box sx={{ p: 2 }}>
						<ReceiptsPagination count={count} page={page} pageSize={pageSize} onPageChange={setPage} />
					</Box>
				</Card>
			</ReceiptsSelectionProvider>

			{/* Headless list to fetch and compute, exposing current paged rows to parent */}
			<ReceiptsList
				filters={filters}
				sortDir={sortDir}
				page={page}
				pageSize={pageSize}
				onCountChange={setCount}
				onStatsChange={setStats}
				renderTable={false}
				onRowsChange={setRows}
			/>
			{/* Uploader lives below the table card as its own component */}
			<Card>
				<Box sx={{ p: 2 }}>
					<ReceiptUploadWidget />
				</Box>
			</Card>
		</Stack>
	);
}

export default ReceiptsContent;
