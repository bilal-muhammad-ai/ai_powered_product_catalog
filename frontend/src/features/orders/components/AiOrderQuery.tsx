import { useEffect, useState } from "react"
import { getProduct } from "../../../api/resources"
import { Field } from "../../../components/ui"
import { suggestOrder, type AiProductMatch } from "../api"
import {
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
  onClear,
  onPendingChange,
  onExcludedChange,
}: {
  onUpsert: (index: number, match: AiProductMatch, price: string, quantity: string) => void
  onClear: () => void
  onPendingChange: (pending: boolean) => void
  onExcludedChange: (names: string[]) => void
}) {
  const [text, setText] = useState("")
  const [items, setItems] = useState<ResolvedAiItem[]>([])
  const [cursor, setCursor] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [choosing, setChoosing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [failed, setFailed] = useState<Record<number, string>>({})

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

  async function addPriced(item: ResolvedAiItem, match: AiProductMatch) {
    const product = await getProduct(match.product_id)
    onUpsert(item.index, match, String(product.selling_price), item.quantity)
    setFailed((currentFailed) => {
      const next = { ...currentFailed }
      delete next[item.index]
      return next
    })
  }

  async function find() {
    const query = text.trim()
    if (!query || loading) return
    setLoading(true)
    setError(null)
    setFailed({})
    setItems([])
    setCursor(null)
    publish([])
    onClear()
    try {
      const resolved = resolveAiOrder(await suggestOrder(query))
      setItems(resolved)
      setCursor(firstPendingChoice(resolved))
      publish(resolved)
      const singles = resolved.filter((item) => item.products.length === 1)
      const problems = await Promise.all(
        singles.map(async (item) => {
          try {
            await addPriced(item, item.products[0])
            return null
          } catch (reason) {
            return { index: item.index, message: reason instanceof Error ? reason.message : "Could not load the product price" }
          }
        }),
      )
      const nextFailed: Record<number, string> = {}
      for (const problem of problems) {
        if (problem) nextFailed[problem.index] = problem.message
      }
      setFailed(nextFailed)
      if (resolved.length === 0) setError("No products were found in that description.")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not read that order")
    } finally {
      setLoading(false)
    }
  }

  async function retry(item: ResolvedAiItem, match: AiProductMatch) {
    try {
      await addPriced(item, match)
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Could not load the product price"
      setFailed((currentFailed) => ({ ...currentFailed, [item.index]: message }))
    }
  }

  async function choose(productId: string) {
    if (!current || choosing) return
    const match = current.products.find((product) => product.product_id === productId)
    if (!match) return
    setChoosing(true)
    setError(null)
    try {
      await addPriced(current, match)
      const nextItems = selectAiItem(items, current.index, productId)
      setItems(nextItems)
      setCursor(firstPendingChoice(nextItems))
      publish(nextItems)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load the product price")
    } finally {
      setChoosing(false)
    }
  }

  function review() {
    const last = choices.at(-1)
    if (last !== undefined) setCursor(last)
  }

  return (
    <div className="rounded-lg border border-copper bg-paper p-4">
      <Field label="Describe the order">
        <textarea
          className="field"
          rows={3}
          value={text}
          placeholder={PLACEHOLDER}
          onChange={(event) => setText(event.target.value)}
        />
      </Field>
      <button className="btn mt-3" type="button" disabled={loading || choosing || text.trim().length === 0} onClick={() => void find()}>
        {loading ? "Finding products…" : "Find products"}
      </button>
      {error ? <p className="mt-3 text-sm text-red-800">{error}</p> : null}
      {items.some((item) => item.products.length === 1 || item.status === "unavailable") ? (
        <ul className="mt-4 grid gap-2">
          {items.map((item) => {
            if (item.products.length === 1) {
              const match = item.products[0]
              const problem = failed[item.index]
              return (
                <li key={item.index} className="rounded-md border border-pine/30 bg-white px-3 py-2 text-sm">
                  <p className="text-xs font-semibold uppercase tracking-wide text-pine">{problem ? "Price unavailable" : "Selected"}</p>
                  <p className="font-medium">{match.name}</p>
                  <p className="text-stone-600">
                    {item.label} · Quantity {item.quantity} {match.selling_unit_symbol}
                  </p>
                  {problem ? (
                    <button className="btn-ghost mt-2" type="button" onClick={() => void retry(item, match)}>
                      Retry
                    </button>
                  ) : null}
                </li>
              )
            }
            if (item.status !== "unavailable") return null
            return (
              <li key={item.index} className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
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
        <fieldset className="mt-4">
          <legend className="text-sm font-semibold text-ink">
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
                  className={`flex cursor-pointer items-start gap-3 rounded-md border bg-white px-3 py-2 text-sm ${selected ? "border-copper" : "border-line"}`}
                >
                  <input
                    type="radio"
                    name={`ai-choice-${current.index}`}
                    value={match.product_id}
                    checked={selected}
                    disabled={choosing}
                    onChange={() => void choose(match.product_id)}
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
            <button
              className="btn-ghost"
              type="button"
              disabled={previousChoice(items, current.index) === null}
              onClick={() => {
                const previous = previousChoice(items, current.index)
                if (previous !== null) setCursor(previous)
              }}
            >
              Back
            </button>
            <button
              className="btn-ghost"
              type="button"
              disabled={current.selectedProductId === null || nextChoice(items, current.index) === null}
              onClick={() => {
                const following = nextChoice(items, current.index)
                if (following !== null) setCursor(following)
              }}
            >
              Next
            </button>
          </div>
        </fieldset>
      ) : null}
      {cursor === null && choices.length > 0 && !hasPendingChoice(items) ? (
        <button className="btn-ghost mt-4" type="button" onClick={review}>
          Review choices
        </button>
      ) : null}
    </div>
  )
}
