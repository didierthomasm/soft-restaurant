import { describe, expect, it, vi } from "vitest";

import { collectAll, pageWindow } from "./pages";

describe("collectAll", () => {
  it("requests pages until it has the total", async () => {
    const data = [1, 2, 3, 4, 5];
    const fetchPage = vi.fn(async (page: number) => ({
      items: data.slice((page - 1) * 2, page * 2),
      total: data.length,
    }));
    await expect(collectAll(fetchPage)).resolves.toEqual(data);
    expect(fetchPage).toHaveBeenCalledTimes(3);
  });

  it("stops on an empty page even if the total says otherwise", async () => {
    const fetchPage = vi.fn(async (page: number) => ({ items: page === 1 ? [1] : [], total: 9 }));
    await expect(collectAll(fetchPage)).resolves.toEqual([1]);
    expect(fetchPage).toHaveBeenCalledTimes(2);
  });

  it("never loops forever", async () => {
    const fetchPage = vi.fn(async () => ({ items: [0], total: 1_000_000 }));
    await expect(collectAll(fetchPage, 3)).resolves.toHaveLength(3);
  });
});

describe("pageWindow", () => {
  it("describes a middle page", () => {
    expect(pageWindow({ total: 65, page: 2, limit: 25 })).toEqual({
      first: 26,
      last: 50,
      lastPage: 3,
      beyond: false,
    });
  });

  it("handles an empty result", () => {
    expect(pageWindow({ total: 0, page: 1, limit: 25 })).toEqual({
      first: 0,
      last: 0,
      lastPage: 1,
      beyond: false,
    });
  });

  it("flags a page past the end", () => {
    expect(pageWindow({ total: 4, page: 3, limit: 25 })).toEqual({
      first: 0,
      last: 0,
      lastPage: 1,
      beyond: true,
    });
  });
});
