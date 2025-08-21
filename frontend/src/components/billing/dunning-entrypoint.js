"use client";

import React from "react";

import { DunningBanner } from "./dunning-banner";
import { PaymentRecoveryDialog } from "./payment-recovery-dialog";

export function DunningEntrypoint() {
	const [open, setOpen] = React.useState(false);
	return (
		<>
			<DunningBanner onFix={() => setOpen(true)} />
			<PaymentRecoveryDialog open={open} onClose={() => setOpen(false)} />
		</>
	);
}
