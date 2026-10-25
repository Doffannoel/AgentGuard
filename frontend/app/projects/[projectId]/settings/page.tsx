import { SettingsPage } from "@/components/pages/settings-page";
export default async function Page({ params }: { params: Promise<{ projectId: string }> }) { const { projectId } = await params; return <SettingsPage projectId={projectId} />; }
