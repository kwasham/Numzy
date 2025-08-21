export enum PlanId {
  FREE = "free",
  PERSONAL = "personal",
  PRO = "pro",
  BUSINESS = "business",
  ENTERPRISE = "business", // alias: treat enterprise as business for now
}

export interface PlanCapability {
  id: PlanId;
  name: string;
  monthlyPrice?: number; // USD for now
  yearlyPrice?: number; // optional when yearly available
  userSeats?: number | "unlimited";
  monthlyQuota?: number; // e.g. documents processed
  retentionDays?: number | "custom";
  prioritySupport?: boolean;
  advancedAnalytics?: boolean;
  sso?: boolean;
  customRetention?: boolean;
}

// Central capability matrix (adjust as strategy evolves)
export const PLAN_CAPABILITIES: Record<PlanId, PlanCapability> = {
  [PlanId.FREE]: {
    id: PlanId.FREE,
    name: "Free",
    monthlyPrice: 0,
    userSeats: 1,
    monthlyQuota: 25,
    retentionDays: 30,
    prioritySupport: false,
    advancedAnalytics: false,
    sso: false,
    customRetention: false,
  },
  [PlanId.PERSONAL]: {
    id: PlanId.PERSONAL,
    name: "Personal",
    monthlyPrice: 9.99,
    userSeats: 1,
    monthlyQuota: 100,
    retentionDays: 180,
    prioritySupport: false,
    advancedAnalytics: false,
    sso: false,
    customRetention: false,
  },
  [PlanId.PRO]: {
    id: PlanId.PRO,
    name: "Pro",
    monthlyPrice: 29,
    userSeats: 10,
    monthlyQuota: 500,
    retentionDays: 365,
    prioritySupport: true,
    advancedAnalytics: true,
    sso: false,
    customRetention: false,
  },
  [PlanId.BUSINESS]: {
    id: PlanId.BUSINESS,
    name: "Business",
    monthlyPrice: 99,
    userSeats: "unlimited",
    monthlyQuota: 5000,
    retentionDays: "custom",
    prioritySupport: true,
    advancedAnalytics: true,
    sso: true,
    customRetention: true,
  },
};

export const DISPLAY_ORDER: PlanId[] = [
  PlanId.FREE,
  PlanId.PERSONAL,
  PlanId.PRO,
  PlanId.BUSINESS,
];

export function availablePlans(
  catalog: Record<string, any>,
  includeFree = true
) {
  return DISPLAY_ORDER.filter((p) => {
    if (p === PlanId.FREE) return includeFree;
    const entry = catalog?.[p];
    // Support both old flat shape { price } and new nested { monthly: { price } }
    const monthly = entry?.monthly?.price ?? entry?.price;
    return typeof monthly === "number";
  });
}
