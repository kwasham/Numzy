export const RECEIPT_CATEGORY_MAP: Record<string, string[]> = {
	"Cost of Goods Sold": [
		"Raw Materials",
		"Direct Labor",
		"Manufacturing Supplies",
		"Freight-In / Shipping for Raw Materials",
		"Packaging Materials",
		"Production Equipment Maintenance",
		"Inventory Shrinkage / Adjustments",
		"Subcontracted Services",
		"Warehousing Costs (if directly tied to goods)",
	],
	"Operational Expenses": [
		"Rent or Lease",
		"Utilities (Electricity, Water, Internet)",
		"Salaries & Wages",
		"Office Supplies",
		"IT & Software Subscriptions",
		"Insurance",
		"Legal and Professional Fees",
		"Repairs and Maintenance",
		"Marketing",
		"Phone and Communication",
		"Vehicle",
		"Fuel",
	],
	"Travel Specific Expenses": [
		"Airfare",
		"Hotels",
		"Ground Transportation (Taxi, Ride-share, Rental Car)",
		"Mileage Reimbursement (for personal vehicle use)",
		"Parking and Tolls",
		"Travel Insurance",
		"Visa Fees or Entry Requirements",
		"Conference or Event Registration (if travel-related)",
	],
	"Meals and Entertainment": [
		"Client Meals",
		"Employee Meals (team outings, working lunches)",
		"Meals While Traveling",
		"Entertainment (client events, shows)",
		"Holiday Parties / Staff Events",
	],
	Other: [
		"Anything used for your business but is not a day to day expense. (Training and development, penalties or fines, bank fees)",
	],
};

export const ALL_SUBCATEGORIES: string[] = Object.values(RECEIPT_CATEGORY_MAP).flat();

export function subcategoriesForCategory(category?: string): string[] {
	if (!category) return ALL_SUBCATEGORIES;
	const list = RECEIPT_CATEGORY_MAP[category];
	return Array.isArray(list) ? list : ALL_SUBCATEGORIES;
}
