export function PageHeading({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-9 flex flex-col justify-between gap-5 border-b border-hairline pb-6 md:flex-row md:items-end">
      <div>
        {eyebrow && <div className="kicker mb-2">{eyebrow}</div>}
        <h1 className="page-title">{title}</h1>
        {description && <p className="mt-3 max-w-3xl text-sm leading-7 text-mute">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
