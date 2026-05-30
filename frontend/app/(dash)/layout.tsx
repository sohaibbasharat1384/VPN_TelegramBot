"use client";

import { AuthProvider, useAuth } from "@/lib/auth";
import { Sidebar } from "@/components/sidebar";
import { ThemeToggle } from "@/components/theme-toggle";
import { Spinner } from "@/components/ui";

function Shell({ children }: { children: React.ReactNode }) {
  const { loading, profile } = useAuth();
  if (loading) return <Spinner />;
  if (!profile) return null; // redirecting to /login
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 items-center justify-between border-b border-border px-6">
          <h2 className="font-semibold">پنل مدیریت</h2>
          <ThemeToggle />
        </header>
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <Shell>{children}</Shell>
    </AuthProvider>
  );
}
