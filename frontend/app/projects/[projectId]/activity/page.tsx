import { ActivityPage } from "@/components/pages/activity-page";
export default async function Page({ params }: { params: Promise<{ projectId: string }> }) { const { projectId } = await params; return <ActivityPage projectId={projectId} />; }
