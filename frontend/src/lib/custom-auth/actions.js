"use server";

import { cookies } from "next/headers";

import { user } from "./data";

function generateToken() {
	const arr = new Uint8Array(12);
	globalThis.crypto.getRandomValues(arr);
	return Array.from(arr, (v) => v.toString(16).padStart(2, "0")).join("");
}

export async function signUp(_) {
	// Store the user in the database
	const token = generateToken();
	const cookieStore = await cookies();
	cookieStore.set("access_token", token);

	return { data: { user } };
}

export async function signInWithOAuth(_) {
	return { error: "Social authentication not implemented" };
}

export async function signInWithPassword(params) {
	const { email, password } = params;

	// We hardcode the credentials for the simplicity of the example
	if (email !== "sofia@devias.io" || password !== "Secret1") {
		return { error: "Invalid credentials" };
	}

	const token = generateToken();
	const cookieStore = await cookies();
	cookieStore.set("access_token", token);

	return { data: { user } };
}

export async function resetPassword(_) {
	return { error: "Password reset not implemented" };
}

export async function updatePassword(_) {
	return { error: "Update reset not implemented" };
}

export async function signOut() {
	const cookieStore = await cookies();
	cookieStore.delete("access_token");

	return {};
}
