export function AsciiLogo({ compact = false }: { compact?: boolean }) {
  if (compact) return <span className="font-bold tracking-tight">[AG] AgentGuard</span>;
  return (
    <div aria-label="AgentGuard" className="ascii-logo">
{` AGENT
 GUARD`}
    </div>
  );
}
