"use client";

import * as React from "react";

export const SettingsContext = React.createContext({
	settings: {},
	setSettings: () => {
		// noop
	},
});

export function SettingsProvider({ children, settings: initialSettings }) {
	const [settings, setSettings] = React.useState(initialSettings);

	React.useEffect(() => {
		setSettings(initialSettings);
	}, [initialSettings]);

	return <SettingsContext.Provider value={{ settings, setSettings }}>{children}</SettingsContext.Provider>;
}

export const SettingsConsumer = SettingsContext.Consumer;

export function useSettings() {
	const context = React.useContext(SettingsContext);

	if (!context) {
		throw new Error("useSettings must be used within a SettingsProvider");
	}

	return context;
}
