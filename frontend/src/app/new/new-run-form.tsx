"use client"

import { useActionState, useState } from "react"
import { Turnstile } from "@marsidev/react-turnstile"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { createRun } from "./actions"
import { EXAMPLES } from "@/lib/examples"

export function NewRunForm({ initialPrompt = "" }: { initialPrompt?: string }) {
  const [state, action, pending] = useActionState(createRun, {})
  const [prompt, setPrompt] = useState(initialPrompt)
  const [idempotencyKey] = useState(() => crypto.randomUUID())

  return (
    <form action={action} className="mt-6 space-y-4">
      <Textarea
        name="prompt"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={6}
        placeholder="Describe the module, the function signatures, and what should happen on bad input."
      />
      <div className="flex flex-wrap justify-center gap-2">
        {EXAMPLES.map((example) => (
          <Badge
            key={example}
            variant="outline"
            className="cursor-pointer"
            onClick={() => setPrompt(example)}
          >
            {example.split(" with ")[0]}
          </Badge>
        ))}
      </div>
      <input type="hidden" name="idempotency_key" value={idempotencyKey} />
      <Turnstile siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY!} />
      {state.error && <p className="text-destructive text-sm">{state.error}</p>}
      <Button type="submit" size="lg" className="w-full" disabled={pending || prompt.trim().length < 10}>
        {pending ? "Starting the factory..." : "Run the factory"}
      </Button>
    </form>
  )
}
