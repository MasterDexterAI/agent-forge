"use client"
/* eslint-disable @typescript-eslint/no-explicit-any */

import { useState, useTransition } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { resumeRun } from "@/app/new/actions"

const REASONS: Record<string, string> = {
  max_iterations: "The Coder tried 3 times and the tests still fail.",
  stuck_same_error: "The Coder hit the same error twice in a row. More retries would waste time.",
  reviewer_not_satisfied: "Tests pass, but the Reviewer keeps asking for changes.",
}

export function HitlDialog({ runId, payload }: { runId: string; payload: Record<string, any> | null }) {
  const [guidance, setGuidance] = useState("")
  const [pending, startTransition] = useTransition()

  const send = (action: "retry" | "replan" | "abort") =>
    startTransition(async () => {
      const result = await resumeRun(runId, action, guidance)
      if (result.error) toast.error(result.error)
      else toast.success(action === "abort" ? "Run stopped." : "Sent. The factory is back on it.")
    })

  return (
    <Dialog open={payload !== null}>
      <DialogContent className="max-w-2xl" showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>The factory needs you</DialogTitle>
          <DialogDescription>
            {REASONS[payload?.reason] ?? "The agents paused for a human decision."}
          </DialogDescription>
        </DialogHeader>
        <pre className="bg-muted max-h-64 overflow-auto rounded p-3 text-xs">
          {payload?.failure || "No failure output."}
        </pre>
        <Textarea
          value={guidance}
          onChange={(e) => setGuidance(e.target.value)}
          rows={4}
          placeholder="Optional hint for the agents, like: the tests expect minutes to allow values above 59"
        />
        <DialogFooter className="gap-2">
          <Button variant="ghost" disabled={pending} onClick={() => send("abort")}>
            Stop
          </Button>
          <Button variant="outline" disabled={pending} onClick={() => send("replan")}>
            Replan
          </Button>
          <Button disabled={pending} onClick={() => send("retry")}>
            Retry with my hint
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
