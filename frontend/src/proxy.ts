import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE, hasSession } from "@/lib/auth/session";

export function proxy(request: NextRequest): NextResponse {
  if (hasSession(request.cookies.get(SESSION_COOKIE)?.value)) {
    return NextResponse.next();
  }
  const { pathname, search } = request.nextUrl;
  if (pathname.startsWith("/backend/")) {
    return NextResponse.json(
      {
        success: false,
        data: null,
        error: { code: "UNAUTHENTICATED", message: "Inicia sesión de nuevo" },
        meta: null,
      },
      { status: 401 },
    );
  }
  const login = new URL("/login", request.url);
  login.searchParams.set("next", `${pathname}${search}`);
  return NextResponse.redirect(login);
}

export const config = {
  matcher: ["/((?!login|auth/|_next/static|_next/image|favicon.ico).*)"],
};
