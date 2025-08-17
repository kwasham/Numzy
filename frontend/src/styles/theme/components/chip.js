import React from "react";
import { chipClasses } from "@mui/material/Chip";
import { XCircleIcon } from "@phosphor-icons/react/dist/ssr/XCircle";

function getSoftVars(color, dark) {
	if (dark) {
		return {
			"--Chip-softBg": `var(--mui-palette-${color}-800)`,
			"--Chip-softColor": `var(--mui-palette-${color}-200)`,
			"--Chip-softDisabledBg": `var(--mui-palette-${color}-800)`,
			"--Chip-softDisabledColor": `var(--mui-palette-${color}-500)`,
			"--Chip-softHoverBg": `var(--mui-palette-${color}-700)`,
			"--Chip-softDeleteIconColor": `var(--mui-palette-${color}-200)`,
			"--Chip-softDeleteIconHoverColor": `var(--mui-palette-${color}-50)`,
		};
	}

	return {
		"--Chip-softBg": `var(--mui-palette-${color}-100)`,
		"--Chip-softColor": `var(--mui-palette-${color}-700)`,
		"--Chip-softDisabledBg": `var(--mui-palette-${color}-50)`,
		"--Chip-softDisabledColor": `var(--mui-palette-${color}-400)`,
		"--Chip-softHoverBg": `var(--mui-palette-${color}-200)`,
		"--Chip-softDeleteIconColor": `var(--mui-palette-${color}-700)`,
		"--Chip-softDeleteIconHoverColor": `var(--mui-palette-${color}-800)`,
	};
}

export const MuiChip = {
	defaultProps: {
		color: "secondary", // default will be removed in material v6
		deleteIcon: <XCircleIcon />,
	},
	styleOverrides: {
		root: { borderRadius: "12px", fontWeight: 500 },
		// Use mode-agnostic CSS variables so colors auto-adapt on theme switch
		outlinedSecondary: () => ({
			borderColor: "var(--mui-palette-divider)",
			color: "var(--mui-palette-text-primary)",
		}),
		soft: ({ ownerState }) => {
			return {
				backgroundColor: "var(--Chip-softBg)",
				color: "var(--Chip-softColor)",
				...(ownerState.disabled && {
					backgroundColor: "var(--Chip-softDisabledBg)",
					color: "var(--Chip-softDisabledColor)",
				}),
				...(ownerState.clickable && { "&:hover": { backgroundColor: "var(--Chip-softHoverBg)" } }),
				[`& .${chipClasses.deleteIcon}`]: {
					color: "var(--Chip-softDeleteIconColor)",
					"&:hover": { color: "var(--Chip-softDeleteIconHoverColor)" },
				},
				"&.Mui-focusVisible": { backgroundColor: "var(--Chip-softHoverBg)" },
			};
		},
		outlinedPrimary: () => ({ borderColor: "var(--mui-palette-divider)", color: "var(--mui-palette-text-primary)" }),
		outlinedInfo: () => ({ borderColor: "var(--mui-palette-divider)", color: "var(--mui-palette-text-primary)" }),
		outlinedSuccess: () => ({ borderColor: "var(--mui-palette-divider)", color: "var(--mui-palette-text-primary)" }),
		outlinedWarning: () => ({ borderColor: "var(--mui-palette-divider)", color: "var(--mui-palette-text-primary)" }),
		outlinedError: () => ({ borderColor: "var(--mui-palette-divider)", color: "var(--mui-palette-text-primary)" }),
		softPrimary: ({ theme }) => {
			return getSoftVars("primary", theme.palette.mode === "dark");
		},
		softSecondary: ({ theme }) => {
			return getSoftVars("secondary", theme.palette.mode === "dark");
		},
		softSuccess: ({ theme }) => {
			return getSoftVars("success", theme.palette.mode === "dark");
		},
		softInfo: ({ theme }) => {
			return getSoftVars("info", theme.palette.mode === "dark");
		},
		softWarning: ({ theme }) => {
			return getSoftVars("warning", theme.palette.mode === "dark");
		},
		softError: ({ theme }) => {
			return getSoftVars("error", theme.palette.mode === "dark");
		},
		iconSmall: { fontSize: "var(--icon-fontSize-sm)" },
		iconMedium: { fontSize: "var(--icon-fontSize-md)" },
	},
};
