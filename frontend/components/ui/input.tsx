import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => (
  <input ref={ref} className={cn("focus-ring h-10 w-full rounded-sm border border-hairline bg-surface-soft px-3 text-sm text-ink placeholder:text-ash focus:bg-canvas focus:border-ink focus:outline-none", className)} {...props} />
));
Input.displayName = "Input";
