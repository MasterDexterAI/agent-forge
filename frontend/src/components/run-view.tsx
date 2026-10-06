"use client"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useRunStream } from "@/hooks/use-run-stream"
import { deriveView } from "@/lib/derive"
import { AgentGraph } from "./agent-graph"
import { FileList } from "./file-tabs"
import { HitlDialog } from "./hitl-dialog"

const STATUS_STYLE: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  approved: "default",
  failed: "destructive",
  aborted: "destructive",
  budget_exceeded: "destructive",
  awaiting_human: "secondary",
}

export function RunView({ runId, token, prompt }: { runId: string; token: string; prompt: string }) {
  const { events, connected } = useRunStream(runId, token)
  const view = deriveView(events)
  const nodeEvents = events.filter((e) => e.kind === "node")

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={STATUS_STYLE[view.status] ?? "outline"}>{view.status.replaceAll("_", " ")}</Badge>
        <Badge variant="outline">iteration {view.iteration}</Badge>
        {view.cost !== null && <Badge variant="outline">${view.cost.toFixed(4)}</Badge>}
        {!connected && view.activeNode && <Badge variant="secondary">reconnecting...</Badge>}
      </div>
      <p className="text-muted-foreground text-sm">{prompt}</p>
      <AgentGraph active={view.activeNode} testPassed={view.testPassed} />

      <Tabs defaultValue="timeline">
        <TabsList>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="plan">Plan</TabsTrigger>
          <TabsTrigger value="tests">Tests</TabsTrigger>
          <TabsTrigger value="code">Code</TabsTrigger>
          <TabsTrigger value="output">Test output</TabsTrigger>
          <TabsTrigger value="review">Review</TabsTrigger>
        </TabsList>

        <TabsContent value="timeline" className="space-y-2">
          {nodeEvents.map((e) => (
            <div key={e.id} className="flex items-center gap-3 text-sm">
              <Badge variant="outline" className="w-28 justify-center">
                {e.data.node}
              </Badge>
              <span className="text-muted-foreground">
                {e.data.node === "tester"
                  ? e.data.test_passed
                    ? "tests passed"
                    : "tests failed"
                  : e.data.node === "coder" && e.data.guard_violation
                    ? `patch rejected: ${e.data.guard_violation}`
                    : e.data.status}
              </span>
            </div>
          ))}
          {nodeEvents.length === 0 && (
            <p className="text-muted-foreground text-sm">Waiting for the Planner...</p>
          )}
        </TabsContent>

        <TabsContent value="plan">
          {view.plan ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{view.plan.summary}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <pre className="bg-muted rounded p-3 text-xs whitespace-pre-wrap">{view.plan.interface}</pre>
                {view.plan.subtasks.map((s) => (
                  <div key={s.id}>
                    <p className="font-medium">
                      {s.id}. {s.title}
                    </p>
                    <ul className="text-muted-foreground ml-5 list-disc">
                      {s.acceptance_criteria.map((c) => (
                        <li key={c}>{c}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : (
            <p className="text-muted-foreground text-sm">No plan yet.</p>
          )}
        </TabsContent>

        <TabsContent value="tests">
          <FileList files={view.tests} empty="Tests not written yet." />
        </TabsContent>
        <TabsContent value="code">
          <FileList files={view.code} empty="No code yet." />
        </TabsContent>

        <TabsContent value="output">
          <pre className="bg-muted max-h-96 overflow-auto rounded p-3 text-xs">
            {view.stdout || view.stderr ? `${view.stdout}\n${view.stderr}` : "Tests have not run yet."}
          </pre>
        </TabsContent>

        <TabsContent value="review">
          {view.review ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  {view.review.verdict} · score {view.review.score.toFixed(2)}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="ml-5 list-disc text-sm">
                  {view.review.comments.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : (
            <p className="text-muted-foreground text-sm">No review yet.</p>
          )}
        </TabsContent>
      </Tabs>

      <HitlDialog runId={runId} payload={view.interrupt} />
    </div>
  )
}
