import type { RunEvent, RunView } from "./types"

export function deriveView(events: RunEvent[]): RunView {
  const view: RunView = {
    activeNode: null,
    plan: null,
    tests: {},
    code: {},
    stdout: "",
    stderr: "",
    testPassed: null,
    iteration: 0,
    review: null,
    status: "queued",
    interrupt: null,
    cost: null,
  }
  for (const event of events) {
    const d = event.data
    if (event.kind === "status") view.status = d.status
    if (event.kind === "interrupt") {
      view.interrupt = d
      view.status = "awaiting_human"
    }
    if (event.kind === "done") {
      view.status = d.status
      view.cost = d.cost_usd ?? null
      view.activeNode = null
    }
    if (event.kind === "error") view.status = "failed"
    if (event.kind !== "node") continue
    view.interrupt = null
    view.activeNode = d.node
    if (d.plan) view.plan = d.plan
    if (d.test_files) view.tests = d.test_files
    if (d.code_files) view.code = d.code_files
    if (d.node === "tester") {
      view.stdout = d.execution_stdout ?? ""
      view.stderr = d.execution_stderr ?? ""
      view.testPassed = d.test_passed ?? null
      view.iteration = d.iteration_count ?? view.iteration
    }
    if (d.review) view.review = d.review
    if (d.status) view.status = d.status
  }
  return view
}
