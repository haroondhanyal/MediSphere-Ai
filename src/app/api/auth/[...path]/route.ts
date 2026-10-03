import { NextRequest, NextResponse } from "next/server";

const apiBase = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const upstream = await fetch(apiBase + "/api/v1/auth/" + path.join("/"), {
    method: request.method,
    headers: {
      "Content-Type": "application/json",
      ...(request.headers.get("cookie") ? { Cookie: request.headers.get("cookie")! } : {}),
    },
    ...(request.method === "POST" ? { body: await request.text() } : {}),
    cache: "no-store",
  });
  const response = new NextResponse(upstream.body, { status: upstream.status });
  const setCookie = upstream.headers.get("set-cookie");
  if (setCookie) response.headers.set("set-cookie", setCookie);
  return response;
}

export const GET = proxy;
export const POST = proxy;
