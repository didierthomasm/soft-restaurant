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

/** Only same-site paths: blocks open redirects such as //evil.com or https://…. */
export function safeNext(value: string | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) {
    return DEFAULT_AFTER_LOGIN;
  }
  return value;
}
