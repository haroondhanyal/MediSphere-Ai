import { NextRequest, NextResponse } from "next/server";

const apiBase = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const upstream = await fetch(apiBase + "/api/v1/" + path.map(encodeURIComponent).join("/") + request.nextUrl.search, {
    method: request.method,
    headers: {
      ...(request.headers.get("content-type") ? { "Content-Type": request.headers.get("content-type")! } : {}),
      ...(request.headers.get("cookie") ? { Cookie: request.headers.get("cookie")! } : {}),
    },
    ...(hasBody ? { body: await request.text() } : {}),
    cache: "no-store",
  });
  const headers = new Headers();
  for (const name of ["content-type", "cache-control", "x-request-id"]) {
    const value = upstream.headers.get(name);
    if (value) headers.set(name, value);
  }
  return new NextResponse(upstream.body, { status: upstream.status, headers });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
