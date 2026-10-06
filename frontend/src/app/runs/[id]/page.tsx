import { notFound, redirect } from "next/navigation"
import { api, currentUserId } from "@/lib/api"
import { RunView } from "@/components/run-view"

export default async function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const userId = await currentUserId()
  if (!userId) redirect("/api/auth/signin")
  const res = await api(`/v1/runs/${id}`, { userId })
  if (!res.ok) notFound()
  const run = await res.json()
  return (
    <main className="mx-auto max-w-5xl p-6">
      <RunView runId={id} token={run.stream_token} prompt={run.prompt} />
    </main>
  )
}
