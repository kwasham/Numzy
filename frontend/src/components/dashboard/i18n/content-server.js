import * as React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { getTranslation } from "@/lib/i18n/server";

export async function ContentServer() {
	const { t } = await getTranslation();

	return (
		<Box sx={{ border: "1px dashed var(--mui-palette-divider)", p: 3 }}>
			<Typography>{t("translations:server")}</Typography>
		</Box>
	);
}
