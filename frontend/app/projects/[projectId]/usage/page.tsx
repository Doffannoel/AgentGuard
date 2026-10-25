import { UsagePage } from "@/components/pages/usage-page";
export default async function Page({ params }: { params: Promise<{ projectId: string }> }) { const { projectId } = await params; return <UsagePage projectId={projectId} />; }
