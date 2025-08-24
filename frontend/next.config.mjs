/** @type {import('next').NextConfig} */
const config = {
	experimental: {
		esmExternals: "loose", // Fix for React PDF Renderer
	},
};

export default config;
