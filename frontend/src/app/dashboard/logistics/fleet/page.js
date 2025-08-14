import * as React from "react";

import { appConfig } from "@/config/app";
import { dayjs } from "@/lib/dayjs";
import { FleetView } from "@/components/dashboard/logistics/fleet-view";

export const metadata = { title: `Fleet | Logistics | Dashboard | ${appConfig.name}` };

const vehicles = [
	{
		id: "VEH-004",
		location: "Brooklyn, New York, United States",
		latitude: 40.683_717,
		longitude: -73.938_242,
		temperature: 6,
		startedAt: dayjs().subtract(21, "minute").subtract(2, "hour").toDate(),
		departedAt: dayjs().subtract(34, "minute").toDate(),
		arrivedAt: dayjs().subtract(9, "minute").toDate(),
	},
	{
		id: "VEH-003",
		location: "Brooklyn, New York, United States",
		latitude: 40.698_211,
		longitude: -73.923_69,
		temperature: 8,
		startedAt: dayjs().subtract(10, "minute").subtract(3, "hour").toDate(),
		departedAt: dayjs().subtract(56, "minute").subtract(2, "hour").toDate(),
		arrivedAt: dayjs().subtract(10, "minute").subtract(1, "hour").toDate(),
	},
	{
		id: "VEH-002",
		location: "Brooklyn, New York, United States",
		latitude: 40.657_431,
		longitude: -73.960_399,
		temperature: 6,
		startedAt: dayjs().subtract(34, "minute").subtract(4, "hour").toDate(),
		departedAt: undefined,
		arrivedAt: undefined,
	},
	{
		id: "VEH-001",
		location: "Brooklyn, New York, United States",
		latitude: 40.675_966,
		longitude: -73.876_617,
		temperature: 8,
		startedAt: dayjs().subtract(9, "minute").subtract(5, "hour").toDate(),
		departedAt: dayjs().subtract(12, "minute").subtract(2, "hour").toDate(),
		arrivedAt: dayjs().subtract(21, "minute").subtract(1, "hour").toDate(),
	},
];

export default function Page() {
	return <FleetView vehicles={vehicles} />;
}
