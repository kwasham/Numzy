import nextJest from "next/jest.js";

const createJestConfig = nextJest({
	dir: "./",
});

/** @type {import('jest').Config} */
const config = {
	testEnvironment: "jest-environment-jsdom",
	moduleNameMapper: {
		"^@/(.*)$": "<rootDir>/src/$1",
		"^@shared/(.*)$": "<rootDir>/../shared/$1",
	},
};

export default createJestConfig(config);
