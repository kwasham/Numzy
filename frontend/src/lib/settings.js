"use server";

import { cookies } from "next/headers";

import { logger } from "@/lib/default-logger";

/**
 * Store settings (partial patch) in client's cookies.
 * This should be used as Server Action.
 *
 * To remove a specific key, set its value to `null`.
 */
export async function setSettings(settings) {
	const cookieStore = await cookies();
	cookieStore.set("settings", JSON.stringify(settings));
}

/**
 * Retrieve the settings from client's cookies.
 * This should be used in Server Components.
 */
export async function getSettings() {
	const cookieStore = await cookies();

	const settingsStr = cookieStore.get("settings")?.value;
	let settings;

	if (settingsStr) {
		try {
			settings = JSON.parse(settingsStr);
		} catch {
			logger.error("Unable to parse the settings");
		}
	}

	settings ||= {};

	return settings;
}
