"use client"

import { ReactFlow, Background, type Edge, type Node } from "@xyflow/react"
import "@xyflow/react/dist/style.css"

const LAYOUT: { id: string; label: string; x: number; y: number }[] = [
  { id: "planner", label: "Planner", x: 0, y: 80 },
  { id: "test_writer", label: "Test Writer", x: 180, y: 80 },
  { id: "coder", label: "Coder", x: 360, y: 80 },
  { id: "tester", label: "Tester", x: 540, y: 80 },
  { id: "reviewer", label: "Reviewer", x: 720, y: 80 },
]

const EDGES: Edge[] = [
  { id: "p-tw", source: "planner", target: "test_writer" },
  { id: "tw-c", source: "test_writer", target: "coder" },
  { id: "c-t", source: "coder", target: "tester" },
  { id: "t-r", source: "tester", target: "reviewer" },
  { id: "r-c", source: "reviewer", target: "coder", label: "fix", type: "smoothstep", animated: true },
  { id: "r-p", source: "reviewer", target: "planner", label: "replan", type: "smoothstep" },
]

export function AgentGraph({ active, testPassed }: { active: string | null; testPassed: boolean | null }) {
  const nodes: Node[] = LAYOUT.map((n) => {
    const isActive = n.id === active
    const failed = n.id === "tester" && testPassed === false
    return {
      id: n.id,
      position: { x: n.x, y: n.y },
      data: { label: n.label },
      draggable: false,
      style: {
        borderRadius: 10,
        padding: 8,
        borderWidth: 2,
        borderColor: isActive ? "var(--primary)" : failed ? "var(--destructive)" : "var(--border)",
        boxShadow: isActive ? "0 0 0 4px color-mix(in oklch, var(--primary) 15%, transparent)" : "none",
        fontWeight: isActive ? 600 : 400,
      },
    }
  })

  return (
    <div className="h-56 w-full rounded-lg border">
      <ReactFlow
        nodes={nodes}
        edges={EDGES}
        fitView
        panOnDrag={false}
        zoomOnScroll={false}
        nodesConnectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background />
      </ReactFlow>
    </div>
  )
}
