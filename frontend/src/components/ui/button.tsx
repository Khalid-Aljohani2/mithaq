import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"
import { Slot } from "radix-ui"

// Controls are printed-form boxes: 2px radius, a solid edge, no shadow.
const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-[var(--radius-ctl)] border font-medium whitespace-nowrap transition-colors select-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        // The one primary action on a view.
        default:
          "border-seal bg-seal text-on-seal hover:bg-[color-mix(in_srgb,var(--seal),var(--ink)_14%)]",
        outline: "border-rule-strong bg-sheet text-ink hover:bg-paper",
        // Reject. Legal red as text and edge, never a filled red block.
        destructive:
          "border-legal bg-sheet text-legal hover:bg-legal-wash",
        // Request revision.
        amber: "border-amber bg-sheet text-amber hover:bg-amber-wash",
        ghost: "border-transparent text-ink hover:bg-paper",
        link: "border-transparent px-0 text-ink underline underline-offset-4 hover:decoration-2",
      },
      size: {
        default: "h-10 px-4 text-sm",
        sm: "h-8 px-3 text-xs",
        lg: "h-11 px-5 text-base",
        icon: "size-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
