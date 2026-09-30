import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { useInvalidate } from "./invalidate";

describe("useInvalidate", () => {
  it("invalidates every given query key", async () => {
    const client = new QueryClient();
    const spy = vi.spyOn(client, "invalidateQueries");
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useInvalidate(["calendar"], ["summary", "2026-09"]), {
      wrapper,
    });
    await result.current();

    expect(spy).toHaveBeenCalledTimes(2);
    expect(spy).toHaveBeenCalledWith({ queryKey: ["calendar"] });
    expect(spy).toHaveBeenCalledWith({ queryKey: ["summary", "2026-09"] });
  });
});
