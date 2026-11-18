export function variantSignature(attributeIds: string[], values: Record<string, unknown>): string {
  return attributeIds
    .slice()
    .sort()
    .map((id) => `${id}:${String(values[id] ?? "")}`)
    .join("|")
}
