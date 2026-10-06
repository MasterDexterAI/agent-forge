"use server"

import { redirect } from "next/navigation"
import { api, currentUserId } from "@/lib/api"

async function verifyTurnstile(token: string): Promise<boolean> {
  const res = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST",
    body: new URLSearchParams({ secret: process.env.TURNSTILE_SECRET_KEY!, response: token }),
  })
  const data = await res.json()
  return data.success === true
}

export async function createRun(_: { error?: string }, formData: FormData): Promise<{ error?: string }> {
  const userId = await currentUserId()
  if (!userId) redirect("/api/auth/signin")

  const token = String(formData.get("cf-turnstile-response") ?? "")
  if (!(await verifyTurnstile(token))) return { error: "Bot check failed. Refresh and try again." }

  const prompt = String(formData.get("prompt") ?? "").trim()
  if (prompt.length < 10) return { error: "Describe what you want in at least a sentence." }
  if (prompt.length > 4000) return { error: "Keep it under 4000 characters." }

  const res = await api("/v1/runs", {
    method: "POST",
    userId,
    body: { prompt, idempotency_key: String(formData.get("idempotency_key") ?? "") },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    return { error: body.detail ?? "Something went wrong. Try again." }
  }
  const { run_id } = await res.json()
  redirect(`/runs/${run_id}`)
}

export async function resumeRun(
  runId: string,
  action: "retry" | "replan" | "abort",
  guidance: string,
): Promise<{ error?: string; ok?: boolean }> {
  const userId = await currentUserId()
  if (!userId) return { error: "Sign in again." }
  const res = await api(`/v1/runs/${runId}/resume`, { method: "POST", userId, body: { action, guidance } })
  if (!res.ok) return { error: (await res.json().catch(() => ({}))).detail ?? "Could not resume." }
  return { ok: true }
}
