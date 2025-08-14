"use client";

import * as React from "react";
import createCache from "@emotion/cache";
import { CacheProvider } from "@emotion/react";
import stylisRTLPlugin from "stylis-plugin-rtl";

function styleCache() {
	return createCache({ key: "mui-rtl", prepend: true, stylisPlugins: [stylisRTLPlugin] });
}

export function Rtl({ children, direction = "ltr" }) {
	if (direction === "rtl") {
		return <CacheProvider value={styleCache()}>{children}</CacheProvider>;
	}

	return <React.Fragment>{children}</React.Fragment>;
}
