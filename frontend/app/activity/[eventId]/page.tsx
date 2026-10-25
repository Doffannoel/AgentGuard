import { ActivityDetailPage } from "@/components/pages/activity-detail-page";
export default async function Page({ params }: { params: Promise<{ eventId: string }> }) { const { eventId } = await params; return <ActivityDetailPage eventId={eventId} />; }
