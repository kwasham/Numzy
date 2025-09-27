import { promises as fs } from "node:fs";
import path from "node:path";

import { NextResponse } from "next/server";

// Serve the marketing homepage content at "/" WITHOUT changing the URL.
// We read the HTML from public and inject a <base> tag so relative assets resolve correctly.
export async function GET() {
	const filePath = path.join(process.cwd(), "public", "marketing-assets", "home-pages", "home-v1.html");

	try {
		let html = await fs.readFile(filePath, "utf8");
		// Rewrite relative asset paths to absolute root-based paths so they resolve from '/'
		html = html
			// CSS links
			.replaceAll('href="../css/', 'href="/css/')
			.replaceAll('href="./css/', 'href="/css/')
			.replaceAll('href="css/', 'href="/css/')
			// JS links
			.replaceAll('src="../js/', 'src="/js/')
			.replaceAll('src="./js/', 'src="/js/')
			.replaceAll('src="js/', 'src="/js/')
			.replaceAll('href="../js/', 'href="/js/')
			.replaceAll('href="./js/', 'href="/js/')
			.replaceAll('href="js/', 'href="/js/')
			// Images
			.replaceAll('src="../images/', 'src="/images/')
			.replaceAll('src="./images/', 'src="/images/')
			.replaceAll('src="images/', 'src="/images/')
			.replaceAll('href="../images/', 'href="/images/')
			.replaceAll('href="./images/', 'href="/images/')
			.replaceAll('href="images/', 'href="/images/');
		return new Response(html, { headers: { "content-type": "text/html; charset=utf-8" } });
	} catch {
		// Fallback: if the file is missing, return a minimal page
		return new Response("<html><body><h1>Home</h1></body></html>", {
			headers: { "content-type": "text/html; charset=utf-8" },
			status: 200,
		});
	}
}

// Handle POST / gracefully (e.g., sign-out callbacks) by redirecting to GET on "/"
export function POST(request: Request) {
	const url = new URL("/", request.url);
	return NextResponse.redirect(url, 303);
}
