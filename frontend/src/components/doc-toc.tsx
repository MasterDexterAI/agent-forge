"use client"

import { useEffect, useState } from "react"
import type { TocItem } from "@/lib/docs"

export function DocToc({ items }: { items: TocItem[] }) {
  const [active, setActive] = useState<string>("")

  useEffect(() => {
    const headings = items.map((i) => document.getElementById(i.id)).filter(Boolean) as HTMLElement[]
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting)
        if (visible.length) setActive(visible[0].target.id)
      },
      { rootMargin: "-80px 0px -70% 0px" },
    )
    headings.forEach((h) => observer.observe(h))
    return () => observer.disconnect()
  }, [items])

  const links = (
    <ul className="space-y-1 text-sm">
      {items.map((item) => (
        <li key={item.id} className={item.level === 3 ? "pl-4" : ""}>
          <a
            href={`#${item.id}`}
            className={`hover:text-foreground block rounded-small px-2 py-1 transition-colors ${
              active === item.id ? "bg-muted text-foreground font-medium" : "text-muted-foreground"
            }`}
          >
            {item.title}
          </a>
        </li>
      ))}
    </ul>
  )

  return (
    <>
      <details className="mb-6 rounded-lg border p-3 lg:hidden">
        <summary className="cursor-pointer text-sm font-medium">On this page</summary>
        <div className="mt-3">{links}</div>
      </details>
      <aside className="sticky top-20 hidden max-h-[calc(100vh-6rem)] w-64 shrink-0 overflow-y-auto pr-2 lg:block">
        <p className="text-text-muted mb-3 px-2 text-xs font-semibold tracking-widest uppercase">On this page</p>
        {links}
      </aside>
    </>
  )
}
