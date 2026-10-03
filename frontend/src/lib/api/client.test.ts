import { describe, expect, it } from "vitest";

import { ApiError, isSrUnavailable, unwrap, unwrapPage } from "./client";

const response = (status: number) => ({ status }) as Response;

describe("unwrap", () => {
  it("returns the envelope data on success", async () => {
    const request = Promise.resolve({ data: { success: true, data: [1, 2] }, response: response(200) });
    await expect(unwrap(request)).resolves.toEqual([1, 2]);
  });

  it("returns null data for successful deletes", async () => {
    const request = Promise.resolve({ data: { success: true, data: null }, response: response(200) });
    await expect(unwrap(request)).resolves.toBeNull();
  });

  it("throws ApiError with the backend code and message", async () => {
    const body = {
      success: false,
      data: null,
      error: { code: "SR_UNAVAILABLE", message: "No se pudo leer SoftRestaurant. Revisa Tailscale." },
    };
    const request = Promise.resolve({ error: body, response: response(503) });
    const error = await unwrap(request).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "SR_UNAVAILABLE", status: 503 });
    expect(isSrUnavailable(error)).toBe(true);
  });

  it("falls back to HTTP_ERROR when the body is not an envelope", async () => {
    const request = Promise.resolve({ error: "Bad Gateway", response: response(502) });
    await expect(unwrap(request)).rejects.toMatchObject({ code: "HTTP_ERROR", status: 502 });
  });

  it("uses a friendly message for non-envelope 5xx responses", async () => {
    const request = Promise.resolve({ error: "Bad Gateway", response: response(502) });
    await expect(unwrap(request)).rejects.toMatchObject({
      code: "HTTP_ERROR",
      message: "El servidor no responde; intenta de nuevo",
    });
  });

  it("maps network failures to NETWORK_ERROR", async () => {
    const request = Promise.reject(new TypeError("fetch failed"));
    await expect(unwrap(request)).rejects.toMatchObject({ code: "NETWORK_ERROR", status: 0 });
  });
});

describe("unwrapPage", () => {
  it("returns the data and the page meta", async () => {
    const body = { success: true, data: { items: [1] }, meta: { total: 30, page: 2, limit: 25 } };
    const request = Promise.resolve({ data: body, response: response(200) });
    await expect(unwrapPage(request)).resolves.toEqual({
      data: { items: [1] },
      page: { total: 30, page: 2, limit: 25 },
    });
  });

  it("rejects a successful response without page meta", async () => {
    const body = { success: true, data: { items: [] }, meta: null };
    const request = Promise.resolve({ data: body, response: response(200) });
    await expect(unwrapPage(request)).rejects.toMatchObject({ code: "BAD_RESPONSE" });
  });

  it("throws the backend error like unwrap", async () => {
    const body = { success: false, data: null, error: { code: "VALIDATION_ERROR", message: "x" } };
    const request = Promise.resolve({ error: body, response: response(422) });
    await expect(unwrapPage(request)).rejects.toMatchObject({ code: "VALIDATION_ERROR", status: 422 });
  });
});
