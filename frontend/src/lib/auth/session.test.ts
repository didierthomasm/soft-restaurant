import { describe, expect, it } from "vitest";

import {
  SESSION_VALUE,
  credentialsMatch,
  hasSession,
  safeNext,
} from "./session";

const env = { FAKE_AUTH_USER: "demo", FAKE_AUTH_PASSWORD: "secreto" };

describe("credentialsMatch", () => {
  it("accepts only the configured pair", () => {
    expect(credentialsMatch("demo", "secreto", env)).toBe(true);
    expect(credentialsMatch("demo", "otra", env)).toBe(false);
    expect(credentialsMatch("otro", "secreto", env)).toBe(false);
  });

  it("rejects everything when credentials are not configured", () => {
    expect(credentialsMatch("", "", {})).toBe(false);
    expect(
      credentialsMatch("demo", "secreto", { FAKE_AUTH_USER: "demo" }),
    ).toBe(false);
  });
});

describe("hasSession", () => {
  it("requires the exact session value", () => {
    expect(hasSession(SESSION_VALUE)).toBe(true);
    expect(hasSession(undefined)).toBe(false);
    expect(hasSession("forged")).toBe(false);
  });
});

describe("safeNext", () => {
  it("keeps internal paths with their query", () => {
    expect(safeNext("/semana?desde=2026-09-21")).toBe(
      "/semana?desde=2026-09-21",
    );
  });

  it.each([
    undefined,
    "",
    "https://evil.com",
    "//evil.com",
    "/\\evil.com",
    "/\t/evil.com",
    "/\n/evil.com",
    "/\r/evil.com",
    "/.//evil.com",
    "/%2e//evil.com",
    "semana",
  ])("falls back to /calendario for %s", (value) => {
    expect(safeNext(value)).toBe("/calendario");
  });
});
