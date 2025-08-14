import * as Sentry from "@sentry/nextjs";

export async function register() {
	const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
	if (!dsn) return;
	Sentry.init({
		dsn,
		tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? 0),
		profilesSampleRate: Number(process.env.SENTRY_PROFILES_SAMPLE_RATE ?? 0),
		release: process.env.SENTRY_RELEASE,
		environment: process.env.NODE_ENV,
	});
}

