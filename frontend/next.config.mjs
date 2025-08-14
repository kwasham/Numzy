/**
 * Next.js configuration.
 *
 * Dynamic require warnings (triggered by some vendor libs like OpenTelemetry / sdk peers)
 * are noisy but benign for local DX. We suppress them ONLY in development so that
 * production / CI builds still surface any newly introduced truly problematic patterns.
 *
 * To force a strict build locally (see all warnings) run: `pnpm build:strict` which sets
 * NO_SUPPRESS_WARNINGS=1 to skip suppression even in dev.
 */
const config = {
	experimental: {
		esmExternals: "loose", // Fix for React PDF Renderer
	},
	webpack: (cfg) => {
		const suppressionPatterns = [
			/Critical dependency: the request of a dependency is an expression/,
			/Critical dependency: require function is used in a way in which dependencies cannot be statically extracted/,
		];
		const dev = process.env.NODE_ENV === "development";
		const suppress = dev && process.env.NO_SUPPRESS_WARNINGS !== "1";
		if (suppress) {
			cfg.ignoreWarnings = [...(cfg.ignoreWarnings || []), ...suppressionPatterns];
		}
		return cfg;
	},
};

export default config;
