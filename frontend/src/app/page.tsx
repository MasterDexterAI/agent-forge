import Link from "next/link"
import { buttonVariants } from "@/components/ui/button"
import { EXAMPLES } from "@/lib/examples"

const AGENTS = [
  { name: "Planner", note: "writes the interface", color: "bg-accent-purple" },
  { name: "Test Writer", note: "tests before code, locked", color: "bg-accent-blue" },
  { name: "Coder", note: "makes the tests pass", color: "bg-accent-orange" },
  { name: "Tester", note: "gVisor sandbox, no network", color: "bg-accent-pink" },
  { name: "Reviewer", note: "approve, fix or escalate", color: "bg-accent-green" },
]

export default function Home() {
  return (
    <main className="mx-auto max-w-5xl px-6">
      <section className="flex min-h-[70vh] flex-col items-center justify-center py-20 text-center">
        <span className="text-text-muted mb-5 rounded-full border px-3 py-1 text-xs font-medium">
          Open source · 5 free runs a day
        </span>
        <h1 className="max-w-3xl text-4xl font-bold tracking-tight text-balance sm:text-6xl">
          Four AI agents. One prompt. Tested code.
        </h1>
        <p className="text-muted-foreground mt-5 max-w-2xl text-lg text-balance">
          A Planner, a Test Writer, a Coder and a Reviewer work together in real time. The tests are
          written before the code and locked, so the agents cannot grade their own homework.
        </p>
        <div className="mt-8 flex flex-col items-center gap-3">
          <Link href="/new" className={buttonVariants({ size: "lg" })}>
            Try it
          </Link>
          <span className="text-text-muted text-sm">Standard library Python for now.</span>
        </div>
      </section>

      <section className="pb-16">
        <div className="grid gap-3 sm:grid-cols-5">
          {AGENTS.map((a) => (
            <div key={a.name} className="bg-background-tertiary rounded-lg border p-4">
              <span className={`${a.color} mb-3 block size-2 rounded-full`} />
              <p className="text-sm font-semibold">{a.name}</p>
              <p className="text-muted-foreground mt-1 text-xs">{a.note}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="pb-24 text-center">
        <h2 className="text-text-muted mb-4 text-xs font-semibold tracking-widest uppercase">
          Start from an example
        </h2>
        <div className="grid gap-3 text-left sm:grid-cols-3">
          {EXAMPLES.map((example) => (
            <Link
              key={example}
              href={`/new?prompt=${encodeURIComponent(example)}`}
              className="hover:border-border-thick hover:bg-background-secondary rounded-lg border p-4 text-sm transition-colors"
            >
              {example}
            </Link>
          ))}
        </div>
      </section>
    </main>
  )
}
