/** @type {import('next').NextConfig} */
const config = {
	experimental: {
		esmExternals: "loose", // Fix for React PDF Renderer
	},
	webpack: (cfg) => {
		// Suppress noisy critical dependency warning from require-in-the-middle (OpenTelemetry/Sentry)
		cfg.ignoreWarnings = [
			...(cfg.ignoreWarnings || []),
			(w) =>
				Boolean(
					w?.message &&
						/warning.+Critical dependency: require function is used/.test(String(w.message)) &&
						w?.module?.resource?.includes?.("require-in-the-middle")
				),
		];
		return cfg;
	},
};

export default config;
