import type { HTMLAttributes } from "react"

const tones = {
  neutral: "bg-stone-100 text-stone-700",
  pine: "bg-pine/10 text-pine",
  copper: "bg-copper/10 text-copper",
  warning: "bg-amber-50 text-amber-900",
  danger: "bg-red-50 text-red-800",
} as const

export function Badge({
  tone = "neutral",
  className = "",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: keyof typeof tones }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${tones[tone]} ${className}`.trim()}
      {...props}
    />
  )
}
