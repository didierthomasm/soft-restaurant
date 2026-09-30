/**
 * FAKE LOGIN (spec D4). This is NOT security: a single demo user from env vars and a
 * constant cookie. Everything auth-related lives here so real auth can replace it.
 */

export const SESSION_COOKIE = "tc_session";
export const SESSION_VALUE = "fake-session";
export const SESSION_MAX_AGE_S = 60 * 60 * 12;
const DEFAULT_AFTER_LOGIN = "/semana";

type Env = Record<string, string | undefined>;

export function credentialsMatch(user: string, password: string, env: Env = process.env): boolean {
  const expectedUser = env.FAKE_AUTH_USER;
  const expectedPassword = env.FAKE_AUTH_PASSWORD;
  if (!expectedUser || !expectedPassword) return false;
  return user === expectedUser && password === expectedPassword;
}

export function hasSession(cookieValue: string | undefined): boolean {
  return cookieValue === SESSION_VALUE;
}

// Control chars (tab/CR/LF are stripped by the URL parser, turning "/\t/x" into "//x") and backslashes.
const UNSAFE_CHARS = /[\u0000-\u001f\u007f\\]/;

/** Only same-site paths: blocks open redirects such as //evil.com or https://…. */
export function safeNext(value: string | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || UNSAFE_CHARS.test(value)) {
    return DEFAULT_AFTER_LOGIN;
  }
  // Dot segments ("/.//evil.com") normalize to "//evil.com": verify the parsed result too.
  const url = new URL(value, "http://x");
  if (url.origin !== "http://x" || url.pathname.startsWith("//")) return DEFAULT_AFTER_LOGIN;
  return url.pathname + url.search + url.hash;
}
