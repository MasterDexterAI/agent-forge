/* eslint-disable @typescript-eslint/no-explicit-any */
import Link from "next/link"
import { redirect } from "next/navigation"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { api, currentUserId } from "@/lib/api"

export default async function RunsPage() {
  const userId = await currentUserId()
  if (!userId) redirect("/api/auth/signin")
  const res = await api("/v1/runs", { userId })
  const { runs = [] } = res.ok ? await res.json() : {}

  return (
    <main className="mx-auto max-w-5xl p-6 py-12">
      <h1 className="mb-8 text-center text-3xl font-bold tracking-tight">My runs</h1>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Prompt</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Iterations</TableHead>
            <TableHead>Cost</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {runs.map((r: any) => (
            <TableRow key={r.id}>
              <TableCell className="max-w-md truncate">
                <Link href={`/runs/${r.id}`} className="hover:underline">
                  {r.prompt}
                </Link>
              </TableCell>
              <TableCell>
                <Badge variant="outline">{r.status}</Badge>
              </TableCell>
              <TableCell>{r.iterations}</TableCell>
              <TableCell>${Number(r.cost_usd).toFixed(4)}</TableCell>
            </TableRow>
          ))}
          {runs.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-muted-foreground text-center">
                No runs yet. <Link href="/new" className="underline">Start one</Link>.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </main>
  )
}
