import * as Sentry from "@sentry/nextjs";

// Single canonical instrumentation entrypoint for the App Router.
// Next.js will call register() very early (both server & edge where applicable).
export async function register() {
	const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
	if (!dsn) return; // Gracefully no-op if Sentry not configured

	Sentry.init({
		dsn,
		tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? 0),
		profilesSampleRate: Number(process.env.SENTRY_PROFILES_SAMPLE_RATE ?? 0),
		release: process.env.NEXT_PUBLIC_SENTRY_RELEASE || process.env.SENTRY_RELEASE,
		environment: process.env.NODE_ENV,
		// Scrub obvious PII keys (example – adjust as needed)
		beforeSend(event) {
			if (event.request?.headers) {
				const h = event.request.headers;
				delete h["authorization"]; // strip auth headers
				delete h["cookie"]; // remove cookies
			}
			return event;
		},
	});

	// Optionally attach build metadata (only if exposed as public env vars)
	try {
		Sentry.setTags({
			ui_lib: "mui",
		});
		} catch {
			// non-fatal
		}
}
