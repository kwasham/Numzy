// Palette augmentation for custom sign-in theme tokens.
// This lets TypeScript know about nested palette keys like theme.palette.neutral.colors100
// without having to cast to any everywhere.
import "@mui/material/styles";

declare module "@mui/material/styles" {
	interface Palette {
		neutral: {
			colors100: string;
			colors200: string;
			colors300: string;
			colors400: string;
			colors500: string;
			colors600: string;
			colors700: string;
			colors800: string;
		};
		companies: {
			logoColors100: string;
			logoColors200: string;
			logoColors300: string;
			logoColors400: string;
			logoColors500: string;
			logoColors600: string;
			logoColors700: string;
			colorsFacebook: string;
			colorsGmail: string;
			colorsGoogleColor1: string;
			colorsGoogleColor2: string;
			colorsGoogleColor3: string;
			colorsGoogleColor4: string;
			colorsLinkedin: string;
			colorsPinterest: string;
			colorsTelegram: string;
			colorsTwitch: string;
			colorsTwitter: string;
			colorsWebflow: string;
			colorsWhatsapp: string;
			colorsX: string;
			colorsYoutube: string;
			colorsZapier: string;
		};
		system: {
			colorsBlue100: string;
			colorsBlue200: string;
			colorsBlue300: string;
			colorsBlue400: string;
			colorsGreen100: string;
			colorsGreen200: string;
			colorsGreen300: string;
			colorsGreen400: string;
			colorsOrange100: string;
			colorsOrange200: string;
			colorsOrange300: string;
			colorsOrange400: string;
			colorsRed100: string;
			colorsRed200: string;
			colorsRed300: string;
			colorsRed400: string;
		};
		other: {
			overlay: string;
			overlay30: string;
			overlay40: string;
			overlay60: string;
		};
		illustrations: {
			color1: string;
			color2: string;
		};
	}
	interface PaletteOptions {
		neutral?: Partial<Palette["neutral"]>;
		companies?: Partial<Palette["companies"]>;
		system?: Partial<Palette["system"]>;
		other?: Partial<Palette["other"]>;
		illustrations?: Partial<Palette["illustrations"]>;
	}
}
