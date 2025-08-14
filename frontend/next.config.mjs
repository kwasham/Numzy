/** @type {import('next').NextConfig} */
const config = {
	experimental: {
		esmExternals: "loose", // Fix for React PDF Renderer
	},
	webpack: (cfg) => {
		cfg.ignoreWarnings = cfg.ignoreWarnings || [];
		cfg.ignoreWarnings.push(/Critical dependency: the request of a dependency is an expression/);
		return cfg;
	},
};

export default config;
