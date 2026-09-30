import createClient from "openapi-fetch";

import type { paths } from "./schema";

/** Browser-only client: `/backend/*` is rewritten by Next to the FastAPI backend. */
export const api = createClient<paths>({ baseUrl: "/backend" });

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ErrorBody = { code: string; message: string };
type Enveloped<T> = { success: boolean; data?: T | null; error?: ErrorBody | null };
type FetchResult<T> = { data?: Enveloped<T>; error?: unknown; response: Response };

function errorBody(value: unknown): ErrorBody | null {
  if (typeof value !== "object" || value === null || !("error" in value)) return null;
  const error = (value as { error: unknown }).error;
  if (typeof error !== "object" || error === null) return null;
  const { code, message } = error as Partial<ErrorBody>;
  return typeof code === "string" && typeof message === "string" ? { code, message } : null;
}

export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>;
  try {
    result = await request;
  } catch {
    throw new ApiError("NETWORK_ERROR", "No se pudo conectar con el servidor", 0);
  }
  const { data, error, response } = result;
  if (data?.success) return (data.data ?? null) as T;
  const body = errorBody(error ?? data);
  throw new ApiError(
    body?.code ?? "HTTP_ERROR",
    body?.message ?? `Error ${response.status}`,
    response.status,
  );
}

export function isSrUnavailable(error: unknown): boolean {
  return error instanceof ApiError && error.code === "SR_UNAVAILABLE";
}
