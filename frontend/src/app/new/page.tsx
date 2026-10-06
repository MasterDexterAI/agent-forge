import { redirect } from "next/navigation"
import { api, currentUserId } from "@/lib/api"
import { NewRunForm } from "./new-run-form"

export default async function NewRunPage({
  searchParams,
}: {
  searchParams: Promise<{ prompt?: string }>
}) {
  const userId = await currentUserId()
  if (!userId) redirect("/api/auth/signin")
  const { prompt } = await searchParams

  const quotaRes = await api("/v1/quota", { userId }).catch(() => null)
  const quota = quotaRes?.ok ? await quotaRes.json() : null

  return (
    <main className="mx-auto max-w-3xl p-6 py-12">
      <h1 className="text-center text-3xl font-bold tracking-tight">What should the factory build?</h1>
      <p className="text-muted-foreground mt-2 text-center text-sm">
        Small Python modules work best. Standard library only, no network.
        {quota && ` ${quota.remaining} of ${quota.limit} runs left today.`}
      </p>
      <NewRunForm initialPrompt={prompt ?? ""} />
    </main>
  )
}
