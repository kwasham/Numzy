// App Router instrumentation entrypoint (Next.js). Even if unused currently,
// exporting an empty register function prevents lint "empty file" violations
// and provides a future hook for analytics/telemetry initialization.
export function register() {
	if (process.env.NEXT_PUBLIC_DEBUG_RECEIPTS === "true") {
		// Lightweight debug marker so we can confirm instrumentation loaded.
		console.debug("[instrumentation] register()");
	}
}
