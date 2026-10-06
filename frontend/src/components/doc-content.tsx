"use client"

import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import rehypeSlug from "rehype-slug"

export function DocContent({ source }: { source: string }) {
  return (
    <article
      className="prose prose-neutral max-w-none
        prose-headings:scroll-mt-24 prose-headings:font-semibold prose-headings:tracking-tight
        prose-h1:text-4xl prose-h2:mt-14 prose-h2:border-b prose-h2:pb-2 prose-h2:text-2xl
        prose-h3:mt-8 prose-h3:text-lg
        prose-p:leading-7 prose-li:leading-7
        prose-a:text-accent-blue prose-a:no-underline hover:prose-a:underline
        prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:text-[0.85em] prose-code:font-medium prose-code:before:content-none prose-code:after:content-none
        prose-pre:rounded-lg prose-pre:border prose-pre:bg-background-secondary prose-pre:text-foreground
        prose-hr:my-10"
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSlug]}
        components={{
          table: ({ children }) => (
            <div className="not-prose my-6 overflow-x-auto rounded-lg border">
              <table className="w-full text-left text-sm">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-muted">{children}</thead>,
          th: ({ children }) => <th className="px-3 py-2 font-semibold whitespace-nowrap">{children}</th>,
          td: ({ children }) => <td className="border-t px-3 py-2 align-top">{children}</td>,
          pre: ({ children }) => (
            <pre className="overflow-x-auto p-4 text-sm leading-6">{children}</pre>
          ),
        }}
      >
        {source}
      </ReactMarkdown>
    </article>
  )
}
