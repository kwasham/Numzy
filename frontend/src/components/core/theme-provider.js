"use client";

import * as React from "react";
import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider } from "@mui/material/styles";

import { appConfig } from "@/config/app";
import { useSettings } from "@/components/core/settings/settings-context";
import { createTheme } from "@/styles/theme/create-theme";

function CustomThemeProvider({ children }) {
	const { settings } = useSettings();

	const direction = settings.direction ?? appConfig.direction;
	const primaryColor = settings.primaryColor ?? appConfig.primaryColor;

	const theme = createTheme({ direction, primaryColor });

	return (
		<ThemeProvider disableTransitionOnChange theme={theme} defaultMode={appConfig.theme}>
			<CssBaseline />
			{children}
		</ThemeProvider>
	);
}

export { CustomThemeProvider as ThemeProvider };
