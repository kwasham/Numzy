import { ReactNode } from "react";
import { CssBaseline, GlobalStyles, ThemeProvider as MuiThemeProvider } from "@mui/material";
import { createTheme } from "@mui/material/styles";

const signInTheme = createTheme({
	palette: {
		primary: {
			main: "rgba(2, 2, 2, 1)",
		},
		secondary: {
			main: "rgba(74, 58, 255, 1)",
		},
		error: {
			main: "rgba(255, 90, 101, 1)",
		},
		warning: {
			main: "rgba(255, 158, 44, 1)",
		},
		info: {
			main: "rgba(29, 136, 254, 1)",
		},
		success: {
			main: "rgba(5, 193, 104, 1)",
		},
		neutral: {
			colors100: "rgba(255, 255, 255, 1)",
			colors200: "rgba(236, 236, 238, 1)",
			colors300: "rgba(188, 188, 188, 1)",
			colors400: "rgba(155, 155, 166, 1)",
			colors500: "rgba(103, 103, 116, 1)",
			colors600: "rgba(79, 79, 89, 1)",
			colors700: "rgba(21, 21, 24, 1)",
			colors800: "rgba(2, 2, 2, 1)",
		},
		companies: {
			logoColors100: "rgba(74, 58, 255, 1)",
			logoColors200: "rgba(128, 85, 250, 1)",
			logoColors300: "rgba(117, 80, 251, 1)",
			logoColors400: "rgba(106, 74, 252, 1)",
			logoColors500: "rgba(96, 69, 253, 1)",
			logoColors600: "rgba(85, 63, 254, 1)",
			logoColors700: "rgba(13, 10, 44, 1)",
			colorsFacebook: "rgba(51, 127, 255, 1)",
			colorsGmail: "rgba(234, 67, 53, 1)",
			colorsGoogleColor1: "rgba(76, 139, 243, 1)",
			colorsGoogleColor2: "rgba(52, 168, 83, 1)",
			colorsGoogleColor3: "rgba(255, 213, 132, 1)",
			colorsGoogleColor4: "rgba(234, 67, 53, 1)",
			colorsLinkedin: "rgba(0, 119, 183, 1)",
			colorsPinterest: "rgba(230, 0, 35, 1)",
			colorsTelegram: "rgba(3, 155, 229, 1)",
			colorsTwitch: "rgba(148, 77, 255, 1)",
			colorsTwitter: "rgba(29, 155, 240, 1)",
			colorsWebflow: "rgba(20, 110, 245, 1)",
			colorsWhatsapp: "rgba(0, 217, 95, 1)",
			colorsX: "rgba(0, 0, 0, 1)",
			colorsYoutube: "rgba(255, 0, 0, 1)",
			colorsZapier: "rgba(255, 74, 0, 1)",
		},
		system: {
			colorsBlue100: "rgba(234, 244, 255, 1)",
			colorsBlue200: "rgba(143, 195, 255, 1)",
			colorsBlue300: "rgba(29, 136, 254, 1)",
			colorsBlue400: "rgba(8, 108, 217, 1)",
			colorsGreen100: "rgba(222, 242, 230, 1)",
			colorsGreen200: "rgba(127, 220, 164, 1)",
			colorsGreen300: "rgba(5, 193, 104, 1)",
			colorsGreen400: "rgba(17, 132, 91, 1)",
			colorsOrange100: "rgba(255, 243, 228, 1)",
			colorsOrange200: "rgba(255, 209, 155, 1)",
			colorsOrange300: "rgba(255, 158, 44, 1)",
			colorsOrange400: "rgba(213, 105, 27, 1)",
			colorsRed100: "rgba(255, 239, 240, 1)",
			colorsRed200: "rgba(255, 190, 194, 1)",
			colorsRed300: "rgba(255, 90, 101, 1)",
			colorsRed400: "rgba(220, 43, 43, 1)",
		},
		other: {
			overlay: "rgba(0, 0, 0, 0.4)",
			overlay30: "rgba(21, 21, 24, 0.3)",
			overlay40: "rgba(0, 0, 0, 0.4)",
			overlay60: "rgba(2, 2, 2, 0.6)",
		},
		illustrations: {
			color1: "rgba(255, 68, 191, 1)",
			color2: "rgba(81, 167, 246, 1)",
		},
	},
	typography: {
		fontFamily: "Objectivity, Helvetica",
		h1: {
			fontSize: "76px",
			fontWeight: 400,
			letterSpacing: "-3px",
			lineHeight: "82px",
		},
		h2: {
			fontSize: "38px",
			fontWeight: 400,
			letterSpacing: "0px",
			lineHeight: "50px",
		},
		h3: {
			fontSize: "28px",
			fontWeight: 400,
			letterSpacing: "0px",
			lineHeight: "38px",
		},
		h4: {
			fontSize: "25px",
			fontWeight: 500,
			letterSpacing: "0px",
			lineHeight: "35px",
		},
		h5: {
			fontSize: "18px",
			fontWeight: 500,
			letterSpacing: "0px",
			lineHeight: "24px",
		},
		h6: {
			fontSize: "16px",
			fontWeight: 500,
			letterSpacing: "0px",
			lineHeight: "22px",
		},
		subtitle1: {
			fontSize: "24px",
			fontWeight: 400,
			letterSpacing: "0px",
			lineHeight: "38px",
		},
		subtitle2: {
			fontSize: "14px",
			fontWeight: 400,
			letterSpacing: "0px",
			lineHeight: "24px",
		},
		body1: {
			fontSize: "18px",
			fontWeight: 400,
			letterSpacing: "0px",
			lineHeight: "30px",
		},
		body2: {
			fontSize: "16px",
			fontWeight: 400,
			letterSpacing: "0px",
			lineHeight: "28px",
		},
	},
	components: {
		MuiButton: {
			styleOverrides: {
				root: {
					textTransform: "none",
				},
			},
		},
	},
	shadows: [
		"none",
		"0px 2px 6px 0px rgba(20, 20, 43, 0.06)",
		"0px 2px 12px 0px rgba(20, 20, 43, 0.08)",
		"0px 8px 28px 0px rgba(20, 20, 43, 0.1)",
		"0px 14px 42px 0px rgba(20, 20, 43, 0.14)",
		"0px 24px 65px 0px rgba(20, 20, 43, 0.16)",
		"0px 32px 72px 0px rgba(20, 20, 43, 0.24)",
		"0px 4px 10px 0px rgba(74, 58, 255, 0.06)",
		"0px 6px 20px 0px rgba(74, 58, 255, 0.08)",
		"0px 10px 28px 0px rgba(74, 58, 255, 0.12)",
		"0px 4px 10px 0px rgba(20, 20, 43, 0.04)",
		"0px 6px 20px 0px rgba(20, 20, 43, 0.06)",
		"0px 10px 28px 0px rgba(20, 20, 43, 0.1)",
		"0px 4px 4px 0px rgba(2, 2, 2, 0.25)",
		"none",
		"none",
		"none",
		"none",
		"none",
		"none",
		"none",
		"none",
		"none",
		"none",
		"none",
	],
});

interface SignInThemeProviderProps {
	children: ReactNode;
}

export function SignInThemeProvider({ children }: SignInThemeProviderProps) {
	return (
		<MuiThemeProvider theme={signInTheme}>
			<CssBaseline />
			<GlobalStyles
				styles={{
					html: {
						backgroundColor: `${signInTheme.palette.primary.main} !important`,
						minHeight: "100%",
					},
					body: {
						backgroundColor: `${signInTheme.palette.primary.main} !important`,
						minHeight: "100%",
					},
					"#__next": {
						backgroundColor: `${signInTheme.palette.primary.main} !important`,
						minHeight: "100%",
					},
				}}
			/>
			{children}
		</MuiThemeProvider>
	);
}

export { signInTheme };
