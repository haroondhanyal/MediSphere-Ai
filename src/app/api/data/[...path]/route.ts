import { NextRequest, NextResponse } from "next/server";

const apiBase = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const upstream = await fetch(apiBase + "/api/v1/" + path.map(encodeURIComponent).join("/") + request.nextUrl.search, {
    method: request.method,
    headers: {
      "Content-Type": "application/json",
      ...(request.headers.get("cookie") ? { Cookie: request.headers.get("cookie")! } : {}),
    },
    ...(request.method === "POST" ? { body: await request.text() } : {}),
    cache: "no-store",
  });
  return new NextResponse(upstream.body, { status: upstream.status });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
