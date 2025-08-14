import * as Sentry from "@sentry/nextjs";

// Single canonical instrumentation entrypoint for the app router.
// Next.js will call register() during the instrumentation phase.
export async function register() {
	const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
	if (!dsn) return; // Gracefully no-op if Sentry not configured
	Sentry.init({
		dsn,
		tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? 0),
		profilesSampleRate: Number(process.env.SENTRY_PROFILES_SAMPLE_RATE ?? 0),
		release: process.env.SENTRY_RELEASE,
		environment: process.env.NODE_ENV,
	});
}
