export type SpendingTrendSeedPoint = {
	/** Calendar month label (e.g. "Apr 24") used directly by the chart. */
	label: string;
	/** ISO-like identifier for the month (YYYY-MM). Optional but useful for lookups. */
	monthKey: string;
	/** Total spend recorded for the month. */
	spent: number;
	/** Budget target for the month. */
	budget: number;
};

/**
 * Seed dataset with ~18 months of spend and budget values.
 * Enables local testing of the spending trend chart without live metrics.
 */
export const SPENDING_TREND_SEED: SpendingTrendSeedPoint[] = [
	{ label: "Apr 24", monthKey: "2024-04", spent: 2480, budget: 3200 },
	{ label: "May 24", monthKey: "2024-05", spent: 2610, budget: 3200 },
	{ label: "Jun 24", monthKey: "2024-06", spent: 2750, budget: 3350 },
	{ label: "Jul 24", monthKey: "2024-07", spent: 2900, budget: 3400 },
	{ label: "Aug 24", monthKey: "2024-08", spent: 3050, budget: 3450 },
	{ label: "Sep 24", monthKey: "2024-09", spent: 3125, budget: 3500 },
	{ label: "Oct 24", monthKey: "2024-10", spent: 2980, budget: 3600 },
	{ label: "Nov 24", monthKey: "2024-11", spent: 3250, budget: 3650 },
	{ label: "Dec 24", monthKey: "2024-12", spent: 3380, budget: 3800 },
	{ label: "Jan 25", monthKey: "2025-01", spent: 3550, budget: 3900 },
	{ label: "Feb 25", monthKey: "2025-02", spent: 3425, budget: 3950 },
	{ label: "Mar 25", monthKey: "2025-03", spent: 3760, budget: 4050 },
	{ label: "Apr 25", monthKey: "2025-04", spent: 3890, budget: 4200 },
	{ label: "May 25", monthKey: "2025-05", spent: 4025, budget: 4300 },
	{ label: "Jun 25", monthKey: "2025-06", spent: 4180, budget: 4400 },
	{ label: "Jul 25", monthKey: "2025-07", spent: 4330, budget: 4500 },
	{ label: "Aug 25", monthKey: "2025-08", spent: 4210, budget: 4550 },
	{ label: "Sep 25", monthKey: "2025-09", spent: 4475, budget: 4600 },
];

export type { SpendingTrendSeedPoint as SpendingTrendSeed };
