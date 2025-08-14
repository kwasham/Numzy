"use client";

import * as React from "react";
import { useColorScheme } from "@mui/material";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Mapbox, { Marker } from "react-map-gl/mapbox";

// Map default view state
const VIEW_STATE = {
	latitude: 40.742_815_765_862_65,
	longitude: -73.992_772_404_439_42,
	zoom: 11,
};

export function FleetMap({ onVehicleSelect, currentVehicleId, vehicles = [] }) {
	const { colorScheme } = useColorScheme();

	const mapRef = React.useRef(null);

	const [viewState] = React.useState(() => {
		if (!currentVehicleId) {
			return VIEW_STATE;
		}

		const currentVehicle = vehicles.find((vehicle) => vehicle.id === currentVehicleId);

		if (!currentVehicle) {
			return VIEW_STATE;
		}

		return { latitude: currentVehicle.latitude, longitude: currentVehicle.longitude, zoom: 13 };
	});

	const handleRecenter = React.useCallback(() => {
		const map = mapRef.current;

		if (!map) {
			return;
		}

		const currentVehicle = vehicles.find((vehicle) => vehicle.id === currentVehicleId);

		const flyOptions = currentVehicle
			? { center: [currentVehicle.longitude, currentVehicle.latitude] }
			: { center: [VIEW_STATE.longitude, VIEW_STATE.latitude] };

		map.flyTo(flyOptions);
	}, [vehicles, currentVehicleId]);

	// Recenter if vehicles or current vehicle change
	React.useEffect(() => {
		handleRecenter();
		// eslint-disable-next-line react-hooks/exhaustive-deps -- Expected
	}, [vehicles, currentVehicleId]);

	const mapStyle = colorScheme === "dark" ? "mapbox://styles/mapbox/dark-v9" : "mapbox://styles/mapbox/light-v9";

	if (!process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN) {
		return (
			<Box
				sx={{
					alignItems: "center",
					display: "flex",
					flex: "1 1 auto",
					flexDirection: "column",
					justifyContent: "center",
					overflowY: "auto",
					p: 3,
				}}
			>
				<Stack spacing={2} sx={{ alignItems: "center" }}>
					<Box component="img" src="/assets/error.svg" sx={{ height: "auto", maxWidth: "100%", width: "120px" }} />
					<Stack spacing={1}>
						<Typography sx={{ textAlign: "center" }} variant="h5">
							Map cannot be loaded
						</Typography>
						<Typography color="text.secondary" sx={{ textAlign: "center" }} variant="subtitle2">
							Mapbox API Key is not configured.
						</Typography>
					</Stack>
				</Stack>
			</Box>
		);
	}

	return (
		<Mapbox
			attributionControl={false}
			initialViewState={viewState}
			mapStyle={mapStyle}
			mapboxAccessToken={process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN}
			maxZoom={20}
			minZoom={11}
			ref={mapRef}
		>
			{vehicles.map((vehicle) => (
				<Marker
					key={vehicle.id}
					latitude={vehicle.latitude}
					longitude={vehicle.longitude}
					onClick={() => {
						onVehicleSelect?.(vehicle.id);
					}}
				>
					<Box
						sx={{
							height: "40px",
							width: "40px",
							...(vehicle.id === currentVehicleId && {
								filter: "drop-shadow(0px 0px 4px var(--mui-palette-primary-main))",
							}),
						}}
					>
						<Box alt="Marker" component="img" src="/assets/marker-truck.png" sx={{ height: "100%" }} />
					</Box>
				</Marker>
			))}
		</Mapbox>
	);
}
