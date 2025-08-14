"use client";

import * as React from "react";
import { use } from "i18next";
import { initReactI18next, useTranslation } from "react-i18next";

import { logger } from "@/lib/default-logger";
import { de } from "@/locales/de";
import { en } from "@/locales/en";
import { es } from "@/locales/es";

// eslint-disable-next-line react-hooks/rules-of-hooks
use(initReactI18next)
	.init({
		debug: false,
		ns: Object.keys(en),
		defaultNS: "common",
		fallbackNS: "common",
		fallbackLng: "en",
		resources: {
			de,
			en,
			es,
		},
	})
	// eslint-disable-next-line unicorn/prefer-top-level-await
	.catch((error) => {
		logger.error("[I18nProvider] Failed to initialize i18n", error);
	});

export function I18nProvider({ children, lng = "en" }) {
	const { i18n } = useTranslation();

	React.useEffect(() => {
		i18n.changeLanguage(lng).catch(() => {
			logger.error(`[I18nProvider] Failed to change language to ${lng}`);
		});
	}, [i18n, lng]);

	// eslint-disable-next-line unicorn/prefer-global-this
	if (typeof window === "undefined") {
		i18n.changeLanguage(lng).catch(() => {
			logger.error(`[I18nProvider] Failed to change language to ${lng}`);
		});
	}

	return <React.Fragment>{children}</React.Fragment>;
}
