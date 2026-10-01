import { safeNext } from "@/lib/auth/session";

import { LoginForm } from "./login-form";

type Props = { searchParams: Promise<{ next?: string }> };

export default async function LoginPage({ searchParams }: Props) {
  const { next } = await searchParams;
  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <LoginForm next={safeNext(next)} />
    </main>
  );
}
