import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  const hasSession = Boolean(request.cookies.get("access_token")?.value);
  const pathname = request.nextUrl.pathname;
  const publicAuthRoutes = new Set([
    "/login",
    "/signup",
    "/forgot-password",
    "/reset-password",
  ]);
  const isPublicAuthRoute = publicAuthRoutes.has(pathname);

  if (!hasSession && !isPublicAuthRoute) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (hasSession && (pathname === "/login" || pathname === "/signup")) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
