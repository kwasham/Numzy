import * as Sentry from "@sentry/nextjs";

// Canonical instrumentation entrypoint (only keep this file; remove duplicates under app/).
export async function register() {
	const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
	if (!dsn) return; // no-op if not configured

	Sentry.init({
		dsn,
		tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? 0),
		profilesSampleRate: Number(process.env.SENTRY_PROFILES_SAMPLE_RATE ?? 0),
		release: process.env.NEXT_PUBLIC_SENTRY_RELEASE || process.env.SENTRY_RELEASE,
		environment: process.env.NODE_ENV,
		autoInstrument: {
			http: false,
			graphql: false,
			socketio: false,
			fetch: true, // keep minimal useful client spans if traces enabled later
		},
		beforeSend(event) {
			if (event.request?.headers) {
				const h = event.request.headers;
				delete h["authorization"];
				delete h["cookie"];
			}
			return event;
		},
	});

	try {
		Sentry.setTags({ ui_lib: "mui" });
	} catch {
		// ignore
	}
}
