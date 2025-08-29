import * as React from "react";

// IMPORTANT: To prevent infinite loops, we only reset selection when the semantic
// contents of `keys` change (identity alone is not enough). Callers should still
// memoize `keys`, but we defensively shallow-compare.
export function useSelection(keys = []) {
	const [selected, setSelected] = React.useState(new Set());
	const prevKeysRef = React.useRef([]);

	React.useEffect(() => {
		const prev = prevKeysRef.current;
		let changed = prev.length === keys.length ? false : true;
		if (!changed) {
			for (const [idx, value] of keys.entries()) {
				if (prev[idx] !== value) {
					changed = true;
					break;
				}
			}
		}
		if (changed) {
			prevKeysRef.current = [...keys];
			setSelected(new Set());
		}
		// If not changed, do nothing (prevents update depth loops when parent recreates array)
	}, [keys]);

	const handleDeselectAll = React.useCallback(() => {
		setSelected(new Set());
	}, []);

	const handleDeselectOne = React.useCallback((key) => {
		setSelected((prev) => {
			const copy = new Set(prev);
			copy.delete(key);
			return copy;
		});
	}, []);

	const handleSelectAll = React.useCallback(() => {
		setSelected(new Set(keys));
	}, [keys]);

	const handleSelectOne = React.useCallback((key) => {
		setSelected((prev) => {
			const copy = new Set(prev);
			copy.add(key);
			return copy;
		});
	}, []);

	const selectedAny = selected.size > 0;
	const selectedAll = selected.size === keys.length;

	return {
		deselectAll: handleDeselectAll,
		deselectOne: handleDeselectOne,
		selectAll: handleSelectAll,
		selectOne: handleSelectOne,
		selected,
		selectedAny,
		selectedAll,
	};
}
