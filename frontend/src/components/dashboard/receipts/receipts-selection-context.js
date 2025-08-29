"use client";

import * as React from "react";

import { useSelection } from "@/hooks/use-selection";

function noop() {
	// No operation
}

export const ReceiptsSelectionContext = React.createContext({
	deselectAll: noop,
	deselectOne: noop,
	selectAll: noop,
	selectOne: noop,
	selected: new Set(),
	selectedAny: false,
	selectedAll: false,
});

export function ReceiptsSelectionProvider({ children, receipts = [] }) {
	// Build a stable ids array so we don't trigger selection reset every render when the
	// receipts prop is a new array reference but contains identical ids.
	const prevIdsRef = React.useRef([]);
	const ids = React.useMemo(() => {
		const next = receipts.map((r) => r.id);
		const prev = prevIdsRef.current;
		if (prev.length === next.length && prev.every((v, i) => v === next[i])) {
			return prev; // reuse previous reference to keep useEffect in useSelection from firing
		}
		prevIdsRef.current = next;
		return next;
	}, [receipts]);

	const selection = useSelection(ids);

	return <ReceiptsSelectionContext.Provider value={{ ...selection }}>{children}</ReceiptsSelectionContext.Provider>;
}

export function useReceiptsSelection() {
	return React.useContext(ReceiptsSelectionContext);
}
