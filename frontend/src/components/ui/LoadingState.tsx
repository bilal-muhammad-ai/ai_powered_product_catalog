export function LoadingState({ label }: { label: string }) {
  return (
    <p className="flex items-center gap-2 text-sm text-stone-500" role="status">
      <span className="h-2 w-2 animate-pulse rounded-full bg-copper" aria-hidden="true" />
      {label}
    </p>
  )
}
