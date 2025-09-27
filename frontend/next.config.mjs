/** @type {import('next').NextConfig} */
const config = {
	// Removed experimental.esmExternals; warning indicated it should not be modified unless strictly necessary.
	// If you still need a workaround for a specific CommonJS package, reintroduce selectively.
	async rewrites() {
		return {
			beforeFiles: [
				{
					source: "/pricing", // intercept requests to /pricing
					destination: "/marketing-assets/pricing.html",
				},
				{
					source: "/about", // intercept requests to /about
					destination: "/marketing-assets/about.html",
				},
				{
					source: "/contact", // intercept requests to /contact
					destination: "/marketing-assets/contact-pages/contact-v1.html",
				},
				{
					source: "/blog", // intercept requests to /blog
					destination: "/marketing-assets/blog-pages/blog-v1.html",
				},
				{
					source: "/blog/:path*", // intercept requests to /blog/*
					destination: "/marketing-assets/blog/:path*",
				},
				{
					source: "/careers", // intercept requests to /careers
					destination: "/marketing-assets/careers.html",
				},
				{
					source: "/careers/:path*", // intercept requests to /careers/*
					destination: "/marketing-assets/careers/:path*",
				},
				{
					source: "/features", // intercept requests to /features
					destination: "/marketing-assets/features.html",
				},
        {
          source: "/sign-up",
          destination: "/marketing-assets/utility-pages/sign-up.html",
        }
			],
		};
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
