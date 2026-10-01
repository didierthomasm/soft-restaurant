import { ReviewView } from "@/components/review/review-view";
import { isIsoDate } from "@/lib/dates";

type Props = { searchParams: Promise<{ desde?: string }> };

export default async function RevisionPage({ searchParams }: Props) {
  const { desde } = await searchParams;
  return <ReviewView requestedStart={isIsoDate(desde) ? desde : null} />;
}
