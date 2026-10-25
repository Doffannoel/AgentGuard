import { ApiKeysPage } from "@/components/pages/api-keys-page";
export default async function Page({ params }: { params: Promise<{ projectId: string }> }) { const { projectId } = await params; return <ApiKeysPage projectId={projectId} />; }
