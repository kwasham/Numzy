import { AuthStrategy } from "@/lib/auth-strategy";
import { LogLevel } from "@/lib/logger";

export const appConfig = {
	name: "Devias Kit Pro",
	description: "",
	direction: "ltr",
	language: "en",
	theme: "light",
	themeColor: "#090a0b",
	primaryColor: "neonBlue",
	// Default to WARN to keep logs at a normal level; override via NEXT_PUBLIC_LOG_LEVEL
	logLevel: process.env.NEXT_PUBLIC_LOG_LEVEL || LogLevel.WARN,
	authStrategy: process.env.NEXT_PUBLIC_AUTH_STRATEGY || AuthStrategy.NONE,
};
