import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useEnsurePeriod } from "./period";

const { replace } = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/semana",
}));

describe("useEnsurePeriod", () => {
  beforeEach(() => replace.mockClear());

  it("fills the default period from the browser's local date", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 8, 27, 23, 30)); // Sunday night, local time
    renderHook(() => useEnsurePeriod(null, (today) => `desde=${today}`));
    expect(replace).toHaveBeenCalledWith("/semana?desde=2026-09-27");
    vi.useRealTimers();
  });

  it("does nothing when the period is in the URL", () => {
    renderHook(() => useEnsurePeriod("2026-09-21", (today) => `desde=${today}`));
    expect(replace).not.toHaveBeenCalled();
  });
});
