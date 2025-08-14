import * as React from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { appConfig } from "@/config/app";
import { ContentClient } from "@/components/dashboard/i18n/content-client";
import { ContentServer } from "@/components/dashboard/i18n/content-server";

export const metadata = { title: `i18n | Dashboard | ${appConfig.name}` };

export default function Page() {
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
				<div>
					<Typography variant="h4">Translations</Typography>
				</div>
				<Typography sx={{ fontStyle: "italic" }}>
					Use the buttons in the header to change the language and see how the translations are updated on the server
					and client.
				</Typography>
				<Stack spacing={3}>
					<ContentServer />
					<ContentClient />
				</Stack>
			</Stack>
		</Box>
	);
}
