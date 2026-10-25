export function AsciiBars<T extends { label: string }>({ rows, value, format = (v) => String(v) }: { rows: T[]; value: keyof T; format?: (value: number) => string }) {
  const values = rows.map((row) => Number(row[value] ?? 0));
  const max = Math.max(...values, 1);
  return <div className="space-y-4">{rows.map((row) => { const v = Number(row[value] ?? 0); return <div key={row.label}><div className="mb-1 flex justify-between gap-4 text-xs"><span>{row.label}</span><span className="text-mute">{format(v)}</span></div><div className="ascii-bar"><span style={{ width: `${Math.max(2, (v / max) * 100)}%` }} /></div></div>; })}</div>;
}
