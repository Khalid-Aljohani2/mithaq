import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"
import { Slot } from "radix-ui"

// A stamped label: 2px radius, an edge in the tone colour, wash behind it.
const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center gap-1 rounded-[var(--radius-ctl)] border px-1.5 py-px text-xs font-medium whitespace-nowrap [&>svg]:pointer-events-none [&>svg]:size-3.5",
  {
    variants: {
      variant: {
        neutral: "border-rule-strong bg-sheet text-ink",
        seal: "border-seal bg-seal-wash text-seal",
        amber: "border-amber bg-amber-wash text-amber",
        legal: "border-legal bg-legal-wash text-legal",
        muted: "border-rule bg-paper text-ink-muted",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  }
)

function Badge({
  className,
  variant = "neutral",
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : "span"

  return (
    <Comp
      data-slot="badge"
      data-variant={variant}
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
