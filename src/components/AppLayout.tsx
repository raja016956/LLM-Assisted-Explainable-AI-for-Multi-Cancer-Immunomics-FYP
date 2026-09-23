import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Upload,
  FlaskConical,
  FileText,
  LogOut,
  Search,
  Bell,
  Dna,
} from "lucide-react";
import { onAuthStateChanged, type User } from "firebase/auth";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import { auth } from "@/lib/firebase";
import { logout } from "@/lib/auth";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/upload", label: "Upload Dataset", icon: Upload },
  { to: "/results", label: "Analysis Results", icon: FlaskConical },
  { to: "/reports", label: "Reports", icon: FileText },
] as const;

function getInitials(user: User | null): string {
  if (!user) return "U";

  const name = user.displayName?.trim();

  if (name) {
    const parts = name.split(/\s+/).filter(Boolean);
    return (
      parts
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase() ?? "")
        .join("") || "U"
    );
  }

  return (
    user.email?.trim().charAt(0).toUpperCase() ||
    "U"
  );
}

export function AppLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [user, setUser] = useState<User | null>(auth.currentUser);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
    });

    return unsubscribe;
  }, []);

  const profileName =
    user?.displayName?.trim() ||
    user?.email?.split("@")[0] ||
    "User";

  const profileEmail = user?.email || "";

  const initials = useMemo(
    () => getInitials(user),
    [user],
  );

  async function handleLogout() {
    try {
      await logout();
      window.location.href = "/";
    } catch (error) {
      console.error("[ImmunoXAI] Logout failed:", error);
    }
  }

  return (
    <div className="flex min-h-screen w-full bg-background">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
        <div className="flex h-16 items-center gap-2 border-b border-sidebar-border px-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Dna className="h-5 w-5" />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold text-sidebar-foreground">ImmunoXAI</div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Immunomics Platform
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {nav.map((n) => {
            const active = pathname === n.to;
            const Icon = n.icon;

            return (
              <Link
                key={n.to}
                to={n.to}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/60"
                }`}
              >
                <Icon className="h-4 w-4" />
                {n.label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-sidebar-border p-3">
          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium text-sidebar-foreground hover:bg-sidebar-accent/60"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-border bg-card px-6">
          <div className="flex items-center gap-3">
            <div>
              <h1 className="text-lg font-semibold text-foreground">{title}</h1>

              {subtitle && (
                <p className="text-xs text-muted-foreground">{subtitle}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative hidden md:block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />

              <input
                placeholder="Search datasets, genes, cohorts…"
                className="h-9 w-72 rounded-lg border border-input bg-background pl-9 pr-3 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/20"
              />
            </div>

            <button
              type="button"
              className="relative rounded-lg p-2 text-muted-foreground hover:bg-muted"
              aria-label="Notifications"
            >
              <Bell className="h-4 w-4" />
              <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-primary" />
            </button>

            <div className="flex min-w-0 items-center gap-3">
              <div className="hidden min-w-0 text-right leading-tight sm:block">
                <div className="max-w-48 truncate text-sm font-medium text-foreground">
                  {profileName}
                </div>

                {profileEmail && (
                  <div className="max-w-48 truncate text-xs text-muted-foreground">
                    {profileEmail}
                  </div>
                )}
              </div>

              {user?.photoURL ? (
                <img
                  src={user.photoURL}
                  alt={profileName}
                  referrerPolicy="no-referrer"
                  className="h-9 w-9 shrink-0 rounded-full object-cover ring-2 ring-background"
                  onError={(event) => {
                    event.currentTarget.style.display = "none";
                    event.currentTarget.nextElementSibling?.classList.remove("hidden");
                  }}
                />
              ) : null}

              <div
                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-soft text-sm font-semibold text-primary ${
                  user?.photoURL ? "hidden" : ""
                }`}
                aria-label={profileName}
              >
                {initials}
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-8">{children}</main>
      </div>
    </div>
  );
}
