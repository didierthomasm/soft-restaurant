import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { api } from "./client";
import { useReview } from "./reviews";

vi.mock("./client", () => ({
  api: { GET: vi.fn() },
  unwrap: (request: Promise<unknown>) => request,
}));

describe("useReview", () => {
  it("rechecks the draft on every mount even within the global staleTime", async () => {
    vi.mocked(api.GET).mockResolvedValue({ id: 5, status: "READY", stale: false } as never);
    const client = new QueryClient({
      defaultOptions: { queries: { staleTime: 30_000, retry: false } },
    });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );

    const first = renderHook(() => useReview(5), { wrapper });
    await waitFor(() => expect(first.result.current.data).toBeDefined());
    first.unmount();

    const second = renderHook(() => useReview(5), { wrapper });
    await waitFor(() => expect(api.GET).toHaveBeenCalledTimes(2));
    second.unmount();
  });
});
