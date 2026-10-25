import * as React from "react";
import { cn } from "@/lib/utils";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => (
  <textarea ref={ref} className={cn("focus-ring min-h-28 w-full rounded-sm border border-hairline bg-surface-soft p-3 text-sm text-ink placeholder:text-ash focus:bg-canvas focus:border-ink focus:outline-none", className)} {...props} />
));
Textarea.displayName = "Textarea";
