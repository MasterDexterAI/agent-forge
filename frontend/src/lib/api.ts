import "server-only"
import { auth } from "@/auth"

export async function currentUserId(): Promise<string | null> {
  const session = await auth()
  return (session?.user as { id?: string } | undefined)?.id ?? null
}

export async function api(path: string, init: { method?: string; body?: unknown; userId: string }) {
  return fetch(`${process.env.API_URL}${path}`, {
    method: init.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Key": process.env.INTERNAL_API_KEY!,
      "X-User-Id": init.userId,
    },
    body: init.body ? JSON.stringify(init.body) : undefined,
    cache: "no-store",
  })
}
