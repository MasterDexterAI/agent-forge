import { ScrollArea } from "@/components/ui/scroll-area"

export function FileList({ files, empty }: { files: Record<string, string>; empty: string }) {
  const entries = Object.entries(files)
  if (entries.length === 0) return <p className="text-muted-foreground text-sm">{empty}</p>
  return (
    <div className="space-y-4">
      {entries.map(([path, content]) => (
        <div key={path}>
          <p className="mb-1 font-mono text-xs font-semibold">{path}</p>
          <ScrollArea className="bg-muted h-72 rounded">
            <pre className="p-3 text-xs">{content}</pre>
          </ScrollArea>
        </div>
      ))}
    </div>
  )
}
