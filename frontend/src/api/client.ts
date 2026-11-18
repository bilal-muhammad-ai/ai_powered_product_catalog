export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function messageFromBody(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") {
    return fallback
  }
  const record = body as { detail?: unknown; errors?: { message?: string }[] }
  if (Array.isArray(record.errors) && record.errors.length > 0) {
    return record.errors.map((error) => error.message).filter(Boolean).join("\n")
  }
  if (typeof record.detail === "string") {
    return record.detail
  }
  if (Array.isArray(record.detail)) {
    return record.detail
      .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : ""))
      .filter(Boolean)
      .join("\n")
  }
  return fallback
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  })
  if (response.status === 204) {
    return undefined as T
  }
  const text = await response.text()
  const body = text ? JSON.parse(text) : null
  if (!response.ok) {
    throw new ApiError(response.status, messageFromBody(body, response.statusText))
  }
  return body as T
}
