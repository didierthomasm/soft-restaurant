import type { PageMeta } from "@/lib/api/client";

const MAX_PAGES = 50;

type PageResult<T> = { items: T[]; total: number };

/** Fetches page 1, 2, … until every item is in, an empty page arrives, or maxPages. */
export async function collectAll<T>(
  fetchPage: (page: number) => Promise<PageResult<T>>,
  maxPages: number = MAX_PAGES,
): Promise<T[]> {
  const collected: T[] = [];
  for (let page = 1; page <= maxPages; page += 1) {
    const { items, total } = await fetchPage(page);
    collected.push(...items);
    if (items.length === 0 || collected.length >= total) break;
  }
  return collected;
}

export type PageWindow = { first: number; last: number; lastPage: number; beyond: boolean };

export function pageWindow({ total, page, limit }: PageMeta): PageWindow {
  const lastPage = Math.max(1, Math.ceil(total / limit));
  const beyond = page > lastPage;
  if (total === 0 || beyond) return { first: 0, last: 0, lastPage, beyond };
  return { first: (page - 1) * limit + 1, last: Math.min(page * limit, total), lastPage, beyond };
}
