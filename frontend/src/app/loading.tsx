// Simple shimmer skeleton loader used during route-level suspense boundaries.
// Lightweight (no external deps) and deterministic for streaming.
export default function Loading() {
	return (
		<div
			role="status"
			aria-live="polite"
			aria-busy="true"
			style={{
				padding: "2rem",
				fontFamily: "system-ui",
				display: "flex",
				flexDirection: "column",
				gap: "1rem",
				maxWidth: 640,
				margin: "0 auto",
			}}
		>
			<ShimmerLine width="60%" height={20} />
			<ShimmerLine width="90%" />
			<ShimmerLine width="85%" />
			<div style={{ display: "flex", gap: "0.75rem" }}>
				<ShimmerLine width={120} height={36} rounded />
				<ShimmerLine width={160} height={36} rounded />
			</div>
			<span style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
				Loading content...
			</span>
		</div>
	);
}

function ShimmerLine({
	width = "100%",
	height = 16,
	rounded = false,
}: {
	width?: number | string;
	height?: number;
	rounded?: boolean;
}) {
	return (
		<div
			style={{
				position: "relative",
				background: "linear-gradient(90deg, #e5e7eb 0%, #f3f4f6 20%, #e5e7eb 40%)",
				backgroundSize: "200% 100%",
				animation: "shimmer 1.4s ease-in-out infinite",
				width,
				height,
				borderRadius: rounded ? 8 : 4,
				overflow: "hidden",
			}}
		/>
	);
}

// Inject keyframes once (alternatively could move to global.css)
if (typeof document !== "undefined" && !document.querySelector("#shimmer-keyframes")) {
	const style = document.createElement("style");
	style.id = "shimmer-keyframes";
	style.textContent = `@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }`;
	document.head.append(style);
}
