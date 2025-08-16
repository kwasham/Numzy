"use client";

import Pagination from "@mui/material/Pagination";
import Stack from "@mui/material/Stack";

export function ReceiptsPagination({ count = 0, page = 0, pageSize = 10, onPageChange }) {
	const totalPages = Math.max(1, Math.ceil(count / pageSize));
	return (
		<Stack alignItems="center">
			<Pagination
				color="primary"
				count={totalPages}
				onChange={(_e, newPage) => onPageChange?.(newPage - 1)}
				page={page + 1}
			/>
		</Stack>
	);
}
