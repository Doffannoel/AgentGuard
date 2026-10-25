import * as React from "react";
import { cn } from "@/lib/utils";

export function Select({ className, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn("focus-ring h-10 rounded-sm border border-hairline bg-surface-soft px-3 text-sm focus:border-ink focus:bg-canvas focus:outline-none", className)} {...props} />;
}
