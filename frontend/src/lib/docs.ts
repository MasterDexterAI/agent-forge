import "server-only"
import { readFile } from "node:fs/promises"
import path from "node:path"
import GithubSlugger from "github-slugger"

export type TocItem = { id: string; title: string; level: 2 | 3 }

export async function loadDocumentation() {
  const source = await readFile(path.join(process.cwd(), "content", "documentation.md"), "utf8")
  const slugger = new GithubSlugger()
  const toc: TocItem[] = []
  let inFence = false
  for (const line of source.split("\n")) {
    if (line.startsWith("```")) inFence = !inFence
    if (inFence) continue
    const match = /^(##|###) (.+)$/.exec(line)
    if (!match) continue
    const title = match[2].replace(/[`*_]/g, "").trim()
    // slugger must see every heading in order so duplicate ids match rehype-slug
    const id = slugger.slug(title)
    toc.push({ id, title, level: match[1] === "##" ? 2 : 3 })
  }
  return { source, toc }
}
