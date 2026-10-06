"use client"

import { useEffect, useState } from "react"
import type { RunEvent } from "@/lib/types"

const KINDS = ["status", "node", "interrupt", "done", "error"]

export function useRunStream(runId: string, token: string) {
  const [events, setEvents] = useState<RunEvent[]>([])
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const url = `${process.env.NEXT_PUBLIC_API_URL}/v1/runs/${runId}/stream?token=${encodeURIComponent(token)}`
    const source = new EventSource(url)
    const onEvent = (kind: string) => (e: MessageEvent) => {
      setEvents((prev) =>
        prev.some((x) => x.id === e.lastEventId)
          ? prev
          : [...prev, { id: e.lastEventId, kind, data: JSON.parse(e.data) }],
      )
      if (kind === "done" || kind === "error") source.close()
    }
    KINDS.forEach((kind) => source.addEventListener(kind, onEvent(kind)))
    source.onopen = () => setConnected(true)
    source.onerror = () => setConnected(false)
    return () => source.close()
  }, [runId, token])

  return { events, connected }
}
