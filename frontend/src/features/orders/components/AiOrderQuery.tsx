import { Sparkles } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { Button, Field } from "../../../components/ui"
import { suggestOrder, type AiProductMatch } from "../api"
import {
  appendAiItems,
  choiceIndexes,
  choicePosition,
  firstPendingChoice,
  hasPendingChoice,
  nextChoice,
  previousChoice,
  resolveAiOrder,
  selectAiItem,
  type ResolvedAiItem,
} from "../ai-order"

const PLACEHOLDER = "Describe the order, for example: 2 bags of DG cement, 10 paintbrushes, and one toilet seat."

export function AiOrderQuery({
  onUpsert,
  onPendingChange,
  onExcludedChange,
}: {
  onUpsert: (index: number, match: AiProductMatch, quantity: string) => void
  onPendingChange: (pending: boolean) => void
  onExcludedChange: (names: string[]) => void
}) {
  const [text, setText] = useState("")
  const [items, setItems] = useState<ResolvedAiItem[]>([])
  const itemsRef = useRef(items)
  itemsRef.current = items
  const [cursor, setCursor] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    onPendingChange(hasPendingChoice(items))
    onExcludedChange(items.filter((item) => item.status === "unavailable").map((item) => item.label))
  }, [items, onPendingChange, onExcludedChange])

  function publish(next: ResolvedAiItem[]) {
    onPendingChange(hasPendingChoice(next))
    onExcludedChange(next.filter((item) => item.status === "unavailable").map((item) => item.label))
  }

  const current = cursor === null ? null : (items.find((item) => item.index === cursor) ?? null)
  const position = current ? choicePosition(items, current.index) : null
  const choices = choiceIndexes(items)

  function addSelected(item: ResolvedAiItem, match: AiProductMatch) {
    onUpsert(item.index, match, item.quantity)
  }

  async function find() {
    const query = text.trim()
    if (!query || loading) return
    setLoading(true)
    setError(null)
    try {
      const resolved = resolveAiOrder(await suggestOrder(query))
      const nextItems = appendAiItems(itemsRef.current, resolved)
      const added = nextItems.slice(itemsRef.current.length)
      setItems(nextItems)
      setCursor(firstPendingChoice(nextItems))
      publish(nextItems)
      for (const item of added) {
        if (item.products.length === 1) addSelected(item, item.products[0])
      }
      if (resolved.length === 0) setError("No products were found in that description.")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not read that order")
    } finally {
      setLoading(false)
    }
  }

  function choose(productId: string) {
    if (!current) return
    const match = current.products.find((product) => product.product_id === productId)
    if (!match) return
    setError(null)
    addSelected(current, match)
    const nextItems = selectAiItem(items, current.index, productId)
    setItems(nextItems)
    setCursor(firstPendingChoice(nextItems))
    publish(nextItems)
  }

  function review() {
    const last = choices.at(-1)
    if (last !== undefined) setCursor(last)
  }

  return (
    <div className="rounded-xl border border-pine/20 bg-white p-4 shadow-card">
      <div className="mb-4 flex items-start gap-3 border-b border-line pb-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-pine text-stone-100">
          <Sparkles className="h-4 w-4" aria-hidden="true" />
        </span>
        <div>
          <p className="text-sm font-semibold text-ink">Assisted entry</p>
          <p className="text-sm text-stone-500">Match catalogue products from a short description.</p>
        </div>
      </div>
      <Field label="Describe the order">
        <textarea
          className="field bg-paper"
          rows={3}
          value={text}
          placeholder={PLACEHOLDER}
          onChange={(event) => setText(event.target.value)}
        />
      </Field>
      <Button className="mt-3" disabled={loading || text.trim().length === 0} onClick={() => void find()}>
        {loading ? "Finding products…" : "Find products"}
      </Button>
      {error ? <p className="mt-3 text-sm text-red-800">{error}</p> : null}
      {items.some((item) => item.products.length === 1 || item.status === "unavailable") ? (
        <ul className="mt-4 grid gap-2">
          {items.map((item) => {
            if (item.products.length === 1) {
              const match = item.products[0]
              return (
                <li key={item.index} className="rounded-lg border border-pine/20 bg-paper px-3 py-2 text-sm">
                  <p className="text-xs font-semibold uppercase tracking-wide text-pine">Selected</p>
                  <p className="font-medium">{match.name}</p>
                  <p className="text-stone-600">
                    {item.label} · Quantity {item.quantity} {match.selling_unit_symbol}
                  </p>
                </li>
              )
            }
            if (item.status !== "unavailable") return null
            return (
              <li key={item.index} className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                <p className="font-medium">
                  {item.label}
                  {item.spokenUnit ? ` · Quantity ${item.quantity} ${item.spokenUnit}` : ` · Quantity ${item.quantity}`}
                </p>
                <p>No matching products available</p>
              </li>
            )
          })}
        </ul>
      ) : null}
      {current && position ? (
        <fieldset className="mt-4 rounded-lg border border-line bg-paper p-3">
          <legend className="px-1 text-sm font-semibold text-ink">
            Selecting product {position.current} of {position.total}
          </legend>
          <p className="mt-1 text-sm text-stone-600">
            {current.label} · Quantity {current.quantity}
            {current.spokenUnit ? ` ${current.spokenUnit}` : ""}. Choose one product.
          </p>
          <div className="mt-2 grid gap-2">
            {current.products.map((match) => {
              const selected = current.selectedProductId === match.product_id
              return (
                <label
                  key={match.product_id}
                  className={`flex cursor-pointer items-start gap-3 rounded-lg border bg-white px-3 py-2 text-sm ${selected ? "border-copper ring-2 ring-copper/15" : "border-line"}`}
                >
                  <input
                    type="radio"
                    className="mt-1 accent-copper"
                    name={`ai-choice-${current.index}`}
                    value={match.product_id}
                    checked={selected}
                    onChange={() => choose(match.product_id)}
                  />
                  <span>
                    <span className="block font-medium">{match.name}</span>
                    <span className="block text-stone-500">
                      {match.category_name} · {match.selling_unit_name} ({match.selling_unit_symbol})
                    </span>
                  </span>
                </label>
              )
            })}
          </div>
          <div className="mt-3 flex gap-2">
            <Button
              variant="ghost"
              disabled={previousChoice(items, current.index) === null}
              onClick={() => {
                const previous = previousChoice(items, current.index)
                if (previous !== null) setCursor(previous)
              }}
            >
              Back
            </Button>
            <Button
              variant="ghost"
              disabled={current.selectedProductId === null || nextChoice(items, current.index) === null}
              onClick={() => {
                const following = nextChoice(items, current.index)
                if (following !== null) setCursor(following)
              }}
            >
              Next
            </Button>
          </div>
        </fieldset>
      ) : null}
      {cursor === null && choices.length > 0 && !hasPendingChoice(items) ? (
        <Button variant="ghost" className="mt-4" onClick={review}>
          Review choices
        </Button>
      ) : null}
    </div>
  )
}
