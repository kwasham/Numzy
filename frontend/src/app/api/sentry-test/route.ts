// Deactivated test route.
export const dynamic = 'force-static';
export async function GET() { return new Response('disabled', { status: 404 }); }
