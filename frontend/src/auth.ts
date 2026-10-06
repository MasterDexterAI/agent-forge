import NextAuth from "next-auth"
import type { Provider } from "next-auth/providers"
import Credentials from "next-auth/providers/credentials"
import GitHub from "next-auth/providers/github"

export const DEMO_ENABLED = process.env.NODE_ENV === "development"

const providers: Provider[] = [GitHub]

// Dev-only shortcut: sign in as a fixed fake user. Never registered outside `next dev`.
if (DEMO_ENABLED) {
  providers.push(
    Credentials({
      id: "demo",
      name: "Demo",
      credentials: {},
      authorize: async () => ({ id: "demo-user", name: "Demo User" }),
    }),
  )
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers,
  callbacks: {
    jwt({ token, profile, user }) {
      if (profile?.id) token.githubId = String(profile.id)
      else if (user?.id) token.githubId = user.id
      return token
    },
    session({ session, token }) {
      if (session.user) (session.user as { id?: string }).id = token.githubId as string
      return session
    },
  },
})
