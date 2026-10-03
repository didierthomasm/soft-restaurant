import { redirect } from "next/navigation";

import { legacySummaryHref } from "@/lib/calendar";

type Props = { searchParams: Promise<{ mes?: string }> };

export default async function MesPage({ searchParams }: Props) {
  redirect(legacySummaryHref(await searchParams));
}
