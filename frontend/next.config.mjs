/** @type {import('next').NextConfig} */
const config = {
	experimental: {
		esmExternals: "loose", // Fix for React PDF Renderer
	},
	webpack: (cfg) => {
		const extra = [
			/Critical dependency: the request of a dependency is an expression/,
			/Critical dependency: require function is used in a way in which dependencies cannot be statically extracted/,
		];
		cfg.ignoreWarnings = [...(cfg.ignoreWarnings || []), ...extra];
		return cfg;
	},
};

export default config;
