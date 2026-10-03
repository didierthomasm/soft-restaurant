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

const SERVER_DOWN_MESSAGE = "El servidor no responde; intenta de nuevo";

type ErrorBody = { code: string; message: string };
type Enveloped<T> = {
  success: boolean;
  data?: T | null;
  error?: ErrorBody | null;
  meta?: { [key: string]: unknown } | null;
};
type FetchResult<T> = { data?: Enveloped<T>; error?: unknown; response: Response };

export type PageMeta = { total: number; page: number; limit: number };
export type Paged<T> = { data: T; page: PageMeta };

function errorBody(value: unknown): ErrorBody | null {
  if (typeof value !== "object" || value === null || !("error" in value)) return null;
  const error = (value as { error: unknown }).error;
  if (typeof error !== "object" || error === null) return null;
  const { code, message } = error as Partial<ErrorBody>;
  return typeof code === "string" && typeof message === "string" ? { code, message } : null;
}

async function envelope<T>(request: Promise<FetchResult<T>>): Promise<Enveloped<T>> {
  let result: FetchResult<T>;
  try {
    result = await request;
  } catch {
    throw new ApiError("NETWORK_ERROR", "No se pudo conectar con el servidor", 0);
  }
  const { data, error, response } = result;
  if (data?.success) return data;
  const body = errorBody(error ?? data);
  throw new ApiError(
    body?.code ?? "HTTP_ERROR",
    body?.message ?? fallbackMessage(response.status),
    response.status,
  );
}

export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  return ((await envelope(request)).data ?? null) as T;
}

function pageMeta(meta: Enveloped<unknown>["meta"]): PageMeta {
  const { total, page, limit } = meta ?? {};
  if (typeof total !== "number" || typeof page !== "number" || typeof limit !== "number") {
    throw new ApiError("BAD_RESPONSE", "La respuesta no trae la paginación", 200);
  }
  return { total, page, limit };
}

export async function unwrapPage<T>(request: Promise<FetchResult<T>>): Promise<Paged<T>> {
  const body = await envelope(request);
  return { data: body.data as T, page: pageMeta(body.meta) };
}

function fallbackMessage(status: number): string {
  return status >= 500 ? SERVER_DOWN_MESSAGE : `Error ${status}`;
}

export function isSrUnavailable(error: unknown): boolean {
  return error instanceof ApiError && error.code === "SR_UNAVAILABLE";
}
