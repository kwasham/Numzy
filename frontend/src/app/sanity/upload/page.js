"use client";

import * as React from "react";
import Container from "@mui/material/Container";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { ReceiptUploadWidget } from "@/components/widgets/receipt-upload-widget";

export default function UploadSanityPage() {
	return (
		<Container maxWidth="md" sx={{ py: 4 }}>
			<Stack spacing={3}>
				<Typography variant="h4">Sanity: Upload a Receipt</Typography>
				<ReceiptUploadWidget />
			</Stack>
		</Container>
	);
}
