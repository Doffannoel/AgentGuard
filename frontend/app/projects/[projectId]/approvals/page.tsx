import { ApprovalsPage } from "@/components/pages/approvals-page";
export default async function Page({ params }: { params: Promise<{ projectId: string }> }) { const { projectId } = await params; return <ApprovalsPage projectId={projectId} />; }
