import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "focus-ring inline-flex min-h-9 items-center justify-center gap-2 rounded-sm px-5 text-sm font-medium transition-none disabled:cursor-not-allowed disabled:bg-surface-card disabled:text-ash",
  {
    variants: {
      variant: {
        primary: "border border-ink bg-ink text-canvas active:bg-ink-deep",
        secondary: "border border-hairline-strong bg-canvas text-ink active:bg-surface-soft",
        ghost: "border border-transparent bg-transparent text-ink active:bg-surface-soft",
        danger: "border border-danger bg-canvas text-danger active:bg-surface-soft"
      },
      size: {
        md: "h-9",
        sm: "h-8 px-3 text-xs"
      }
    },
    defaultVariants: { variant: "primary", size: "md" }
  }
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild, ...props }, ref) => {
  const Comp = asChild ? Slot : "button";
  return <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />;
});
Button.displayName = "Button";
