import { NextResponse } from "next/server";

import { SESSION_COOKIE } from "@/lib/auth/session";

export async function POST(): Promise<NextResponse> {
  const response = NextResponse.json({ success: true, data: null, error: null, meta: null });
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
