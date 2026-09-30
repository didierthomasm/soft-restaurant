import { NextResponse } from "next/server";

import {
  SESSION_COOKIE,
  SESSION_MAX_AGE_S,
  SESSION_VALUE,
  credentialsMatch,
} from "@/lib/auth/session";

function field(body: unknown, name: string): string {
  if (typeof body !== "object" || body === null) return "";
  const value = (body as Record<string, unknown>)[name];
  return typeof value === "string" ? value : "";
}

export async function POST(request: Request): Promise<NextResponse> {
  const body: unknown = await request.json().catch(() => null);
  if (!credentialsMatch(field(body, "user"), field(body, "password"))) {
    return NextResponse.json(
      {
        success: false,
        data: null,
        error: { code: "INVALID_CREDENTIALS", message: "Usuario o contraseña incorrectos" },
        meta: null,
      },
      { status: 401 },
    );
  }
  const response = NextResponse.json({ success: true, data: null, error: null, meta: null });
  response.cookies.set(SESSION_COOKIE, SESSION_VALUE, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_MAX_AGE_S,
  });
  return response;
}
