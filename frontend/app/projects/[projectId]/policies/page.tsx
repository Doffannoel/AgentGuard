import { PoliciesPage } from "@/components/pages/policies-page";
export default async function Page({ params }: { params: Promise<{ projectId: string }> }) { const { projectId } = await params; return <PoliciesPage projectId={projectId} />; }
