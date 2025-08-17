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
	const ids = React.useMemo(() => receipts.map((r) => r.id), [receipts]);
	const selection = useSelection(ids);

	return <ReceiptsSelectionContext.Provider value={{ ...selection }}>{children}</ReceiptsSelectionContext.Provider>;
}

export function useReceiptsSelection() {
	return React.useContext(ReceiptsSelectionContext);
}
