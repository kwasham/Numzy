import * as React from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

const brandBgs = {
	mastercard: "/assets/card-background-1.png",
	visa: "/assets/card-background-2.png",
};

const brandIcons = { mastercard: "/assets/logo-mastercard.svg", visa: "/assets/logo-visa.svg" };

export function CreditCard({ card }) {
	// Always mask PAN when rendering UI. For prototypes, prefer last4 only.
	const maskCardNumber = React.useCallback((value) => {
		if (!value) return "•••• •••• •••• ••••";
		const digits = String(value).replaceAll(/\D/g, "");
		const last4 = digits.slice(-4);
		return `•••• •••• •••• ${last4 || "••••"}`;
	}, []);

	const brand = card?.brand === "visa" || card?.brand === "mastercard" ? card.brand : "visa";
	const bg = brandBgs[brand] || brandBgs.visa;
	const logo = brandIcons[brand] || brandIcons.visa;

	return (
		<Stack
			spacing={4}
			sx={{
				bgcolor: "var(--mui-palette-primary-main)",
				backgroundImage: `url("${bg}")`,
				backgroundPosition: "center",
				backgroundRepeat: "no-repeat",
				backgroundSize: "cover",
				p: "32px 24px",
				borderRadius: "20px",
			}}
		>
			<Box sx={{ alignItems: "center", display: "flex", justifyContent: "space-between" }}>
				<Box alt="Contactless" component="img" src="/assets/contactless.svg" sx={{ height: "auto", width: "24px" }} />
				<Box alt={brand} component="img" src={logo} sx={{ height: "auto", width: "56px" }} />
			</Box>
			<Typography
				sx={{
					background: "linear-gradient(180deg, rgba(255, 255, 255, 0.8) 0%, #FFFFFF 100%)",
					backgroundClip: "text",
					fontSize: "1.25rem",
					fontWeight: 700,
					letterSpacing: "0.3em",
					lineHeight: 1.2,
					textFillColor: "transparent",
				}}
			>
				{maskCardNumber(card.cardNumber || card.last4)}
			</Typography>
			<Stack direction="row" spacing={2} sx={{ alignItems: "center", justifyContent: "space-between" }}>
				<div>
					<Typography color="white" variant="caption">
						Card holder
					</Typography>
					<Typography color="white" variant="subtitle2">
						{card.holderName || card.cardholderName || "Cardholder"}
					</Typography>
				</div>
				<div>
					<Typography color="white" variant="caption">
						Expiry date
					</Typography>
					<Typography color="white" variant="subtitle2">
						{card.expiryDate ||
							(card.exp_month && card.exp_year
								? `${String(card.exp_month).padStart(2, "0")}/${String(card.exp_year).slice(-2)}`
								: "MM/YY")}
					</Typography>
				</div>
				<div>
					<Box
						alt="Sim card"
						component="img"
						src="/assets/sim.svg"
						sx={{ display: "block", height: "auto", width: "48px" }}
					/>
				</div>
			</Stack>
		</Stack>
	);
}
