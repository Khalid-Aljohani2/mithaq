import * as React from "react"
import { cn } from "cn"

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "flex min-h-16 w-full rounded-[var(--radius-ctl)] border border-rule-strong bg-sheet px-3 py-2 text-base text-ink placeholder:text-ink-muted disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-legal",
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
