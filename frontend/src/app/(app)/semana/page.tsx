import { redirect } from "next/navigation";

import { legacyWeekHref } from "@/lib/calendar";

type Props = { searchParams: Promise<{ desde?: string; empleado?: string; dia?: string }> };

export default async function SemanaPage({ searchParams }: Props) {
  redirect(legacyWeekHref(await searchParams));
}
