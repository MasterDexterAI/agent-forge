/* eslint-disable @typescript-eslint/no-explicit-any */
export type RunEvent = { id: string; kind: string; data: Record<string, any> }

export type Plan = {
  summary: string
  modules: string[]
  interface: string
  subtasks: { id: number; title: string; description: string; acceptance_criteria: string[] }[]
}

export type Review = { verdict: string; score: number; comments: string[] }

export type RunView = {
  activeNode: string | null
  plan: Plan | null
  tests: Record<string, string>
  code: Record<string, string>
  stdout: string
  stderr: string
  testPassed: boolean | null
  iteration: number
  review: Review | null
  status: string
  interrupt: Record<string, any> | null
  cost: number | null
}
