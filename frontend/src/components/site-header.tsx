import Link from "next/link"
import { DEMO_ENABLED, auth, signIn, signOut } from "@/auth"
import { Button, buttonVariants } from "@/components/ui/button"

export async function SiteHeader() {
  const session = await auth()
  return (
    <header className="bg-background/80 sticky top-0 z-40 border-b backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between p-4">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="bg-primary text-primary-foreground grid size-6 place-items-center rounded-small text-xs">
            AF
          </span>
          Agent Forge
        </Link>
        <nav className="flex items-center gap-1">
          <Link href="/documentation" className={buttonVariants({ variant: "ghost", size: "sm" })}>
            Documentation
          </Link>
          {session?.user ? (
            <>
              <Link href="/new" className={buttonVariants({ variant: "ghost", size: "sm" })}>
                New run
              </Link>
              <Link href="/runs" className={buttonVariants({ variant: "ghost", size: "sm" })}>
                My runs
              </Link>
              <form
                action={async () => {
                  "use server"
                  await signOut({ redirectTo: "/" })
                }}
              >
                <Button variant="outline" size="sm" type="submit">
                  Sign out
                </Button>
              </form>
            </>
          ) : (
            <>
              {DEMO_ENABLED && (
                <form
                  action={async () => {
                    "use server"
                    await signIn("demo", { redirectTo: "/new" })
                  }}
                >
                  <Button size="sm" variant="outline" type="submit">
                    Demo login (dev)
                  </Button>
                </form>
              )}
              <form
                action={async () => {
                  "use server"
                  await signIn("github", { redirectTo: "/new" })
                }}
              >
                <Button size="sm" type="submit">
                  Sign in with GitHub
                </Button>
              </form>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
