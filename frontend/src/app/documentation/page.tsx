import type { Metadata } from "next"
import { DocContent } from "@/components/doc-content"
import { DocToc } from "@/components/doc-toc"
import { loadDocumentation } from "@/lib/docs"

export const metadata: Metadata = {
  title: "Documentation | Agent Forge",
  description: "Learner guide: concepts, setup, deployment and evals.",
}

export default async function DocumentationPage() {
  const { source, toc } = await loadDocumentation()
  // Keep the sidebar to chapters (h2); sub-headings stay in the page body.
  const chapters = toc.filter((t) => t.level === 2)
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="lg:flex lg:gap-10">
        <DocToc items={chapters} />
        <div className="min-w-0 flex-1 lg:max-w-3xl">
          <DocContent source={source} />
        </div>
      </div>
    </main>
  )
}
