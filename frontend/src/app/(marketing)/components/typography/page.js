import * as React from "react";

import { appConfig } from "@/config/app";
import { Layout } from "@/components/widgets/layout";
import { Typography1 } from "@/components/widgets/typography/typography-1";

export const metadata = { title: `Typography | Components | ${appConfig.name}` };

const components = [{ title: "Typography 1", element: <Typography1 /> }];

export default function Page() {
	return <Layout components={components} title="Typography" />;
}
