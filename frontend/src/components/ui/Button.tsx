import type { ButtonHTMLAttributes } from "react"

const variants = {
  primary: "btn",
  ghost: "btn-ghost",
  danger: "btn-danger",
} as const

export function Button({
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof variants }) {
  return <button type={type} className={`${variants[variant]} ${className}`.trim()} {...props} />
}
