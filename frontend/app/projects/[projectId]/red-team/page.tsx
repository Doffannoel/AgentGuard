import { RedTeamPage } from "@/components/pages/red-team-page";
export default async function Page({ params }: { params: Promise<{ projectId: string }> }) { const { projectId } = await params; return <RedTeamPage projectId={projectId} />; }
