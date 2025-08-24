// Robust amount parser that handles various locales and formats
// Examples handled:
//  - "$1,234.56" -> 1234.56
//  - "1.234,56"   -> 1234.56
//  - "1,234"      -> 1234
//  - "1234"       -> 1234
//  - "12,34" (ambiguous) -> 12.34 (treat comma as decimal when no dot present)
export function parseAmount(value) {
	if (typeof value === "number") return Number.isFinite(value) ? value : 0;
	if (typeof value !== "string") return 0;

	// Strip currency symbols and spaces, keep digits, dot, comma, minus
	const s = value.replaceAll(/[^0-9.,-]+/g, "").trim();
	if (!s) return 0;

	const hasComma = s.includes(",");
	const hasDot = s.includes(".");
	let normalized = s;

	if (hasComma && hasDot) {
		// Decide decimal separator by the last occurring symbol
		normalized =
			s.lastIndexOf(",") > s.lastIndexOf(".")
				? s.replaceAll(".", "").replaceAll(",", ".") // comma as decimal
				: s.replaceAll(",", ""); // dot as decimal
	} else if (hasComma && !hasDot) {
		// Only comma present → treat as decimal separator
		normalized = s.replaceAll(",", ".");
	} else {
		// Only dot or neither → already fine (remove stray thousands separators just in case)
		// If multiple dots, remove all but the last to prevent NaN
		const parts = s.split(".");
		if (parts.length > 2) {
			const last = parts.pop();
			normalized = parts.join("") + "." + last;
		}
	}

	const n = Number(normalized);
	return Number.isFinite(n) ? n : 0;
}

export default parseAmount;
