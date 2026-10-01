// @vitest-environment node
import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { SESSION_COOKIE, SESSION_VALUE } from "@/lib/auth/session";
import { proxy } from "@/proxy";

function request(path: string, withSession = false): NextRequest {
  const headers = withSession ? { cookie: `${SESSION_COOKIE}=${SESSION_VALUE}` } : undefined;
  return new NextRequest(`http://localhost${path}`, { headers });
}

describe("proxy", () => {
  it("redirects pages to /login keeping the destination", () => {
    const response = proxy(request("/semana?desde=2026-09-21"));
    expect(response.status).toBe(307);
    const location = new URL(response.headers.get("location") ?? "");
    expect(location.pathname).toBe("/login");
    expect(location.searchParams.get("next")).toBe("/semana?desde=2026-09-21");
  });

  it("answers API calls without session with a 401 envelope", async () => {
    const response = proxy(request("/backend/attendance/calendar"));
    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toMatchObject({
      success: false,
      error: { code: "UNAUTHENTICATED" },
    });
  });

  it("lets requests with a session through", () => {
    const response = proxy(request("/semana", true));
    expect(response.headers.get("x-middleware-next")).toBe("1");
  });
});
