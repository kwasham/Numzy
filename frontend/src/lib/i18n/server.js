import { createInstance } from "i18next";

import { appConfig } from "@/config/app";
import { getSettings as getPersistedSettings } from "@/lib/settings";
import { de } from "@/locales/de";
import { en } from "@/locales/en";
import { es } from "@/locales/es";

async function initI18next() {
	const settings = await getPersistedSettings();
	const language = settings.language ?? appConfig.language;

	const i18nInstance = createInstance();

	await i18nInstance.init({
		debug: false,
		ns: Object.keys(en),
		defaultNS: "common",
		fallbackNS: "common",
		lng: language,
		fallbackLng: "en",
		supportedLngs: ["de", "en", "es"],
		resources: {
			de,
			en,
			es,
		},
	});

	return i18nInstance;
}

export async function getTranslation() {
	const i18nextInstance = await initI18next();

	return {
		t: i18nextInstance.t,
		i18n: i18nextInstance,
	};
}
