import { describe, expect, it } from "vitest";

import { ApiError } from "./client";
import { shouldRetry } from "./retry";

describe("shouldRetry", () => {
  it("does not retry when SR is unavailable", () => {
    const error = new ApiError("SR_UNAVAILABLE", "Revisa Tailscale", 503);
    expect(shouldRetry(0, error)).toBe(false);
  });

  it("does not retry 4xx errors", () => {
    expect(shouldRetry(0, new ApiError("NOT_FOUND", "x", 404))).toBe(false);
  });

  it("retries network and other 5xx errors twice", () => {
    expect(shouldRetry(0, new ApiError("NETWORK_ERROR", "x", 0))).toBe(true);
    expect(shouldRetry(1, new ApiError("HTTP_ERROR", "x", 502))).toBe(true);
    expect(shouldRetry(2, new ApiError("HTTP_ERROR", "x", 502))).toBe(false);
  });
});
