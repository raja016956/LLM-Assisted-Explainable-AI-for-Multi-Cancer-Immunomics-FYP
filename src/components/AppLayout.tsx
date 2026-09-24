// React Router imports for navigation links and current route state.
import { Link, useRouterState } from "@tanstack/react-router";

// Icons used throughout the shared application layout.
import {
  LayoutDashboard,
  Upload,
  FlaskConical,
  FileText,
  LogOut,
  Dna,
} from "lucide-react";

// Firebase authentication types and listener for the logged-in user.
import { onAuthStateChanged, type User } from "firebase/auth";

// React types and hooks used by the layout component.
import type { ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

// Firebase instance and logout helper used by the profile section.
import { auth } from "@/lib/firebase";
import { logout } from "@/lib/auth";

// Shared sidebar navigation items and their corresponding icons.
const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/upload", label: "Upload Dataset", icon: Upload },
  { to: "/results", label: "Analysis Results", icon: FlaskConical },
  { to: "/reports", label: "Reports", icon: FileText },
] as const;

// Creates fallback initials when the Firebase profile does not have a usable photo.
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

// Shared application layout: sidebar navigation, top header, Firebase profile menu, and page content.
export function AppLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  // Reads the current route so the matching sidebar item can be highlighted.
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  // Stores the current Firebase user and profile-menu state.
  const [user, setUser] = useState<User | null>(auth.currentUser);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);

  // Keeps a reference to the profile menu so outside clicks can close it.
  const profileMenuRef = useRef<HTMLDivElement | null>(null);

  // Subscribes to Firebase authentication changes and keeps the user state updated.
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
    });

    return unsubscribe;
  }, []);

  // Closes the profile menu when the user clicks outside of it.
  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (
        profileMenuRef.current &&
        !profileMenuRef.current.contains(event.target as Node)
      ) {
        setProfileMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
    };
  }, []);

  // Firebase profile data: Google provider values are used as a fallback for name and photo.
  const googleProfile = user?.providerData.find(
    (profile) => profile.providerId === "google.com",
  );

  // Builds the name, email, and photo values displayed in the profile area.
  const profileName =
    user?.displayName?.trim() ||
    googleProfile?.displayName?.trim() ||
    user?.email?.split("@")[0] ||
    "User";

  const profileEmail = user?.email || "";
  const profilePhotoUrl =
    user?.photoURL || googleProfile?.photoURL || null;

  // Generates initials for the profile avatar when a profile image is unavailable.
  const initials = useMemo(() => {
    if (profileName && profileName !== "User") {
      const parts = profileName.split(/\s+/).filter(Boolean);
      return (
        parts
          .slice(0, 2)
          .map((part) => part[0]?.toUpperCase() ?? "")
          .join("") || "U"
      );
    }

    return getInitials(user);
  }, [profileName, user]);

  // Signs out the current Firebase user and redirects to the sign-in page.
  async function handleLogout() {
    try {
      await logout();
      setProfileMenuOpen(false);
      window.location.href = "/";
    } catch (error) {
      console.error("[ImmunoXAI] Logout failed:", error);
    }
  }

  // Main shared layout containing the sidebar and the page content area.
  return (
    <div className="flex min-h-screen w-full bg-background">
      {/* Sidebar: branding, navigation links, and logout action. */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
        {/* Application branding and dashboard link. */}
        <div className="border-b border-sidebar-border px-4">
          <Link
            to="/dashboard"
            className="flex h-16 items-center gap-2 rounded-lg px-2 transition-colors hover:bg-sidebar-accent/60"
            aria-label="Go to dashboard"
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Dna className="h-5 w-5" />
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold text-sidebar-foreground">
                ImmunoXAI
              </div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                Immunomics Platform
              </div>
            </div>
          </Link>
        </div>

        {/* Sidebar navigation: highlights the currently active route. */}
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

        {/* Bottom sidebar section containing the logout button. */}
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

      {/* Main application column containing the header and route content. */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top header: page title, subtitle, and user profile menu. */}
        <header className="flex h-16 items-center justify-between border-b border-border bg-card px-6">
          {/* Page title and optional subtitle supplied by each route. */}
          <div className="flex items-center gap-3">
            <div>
              <h1 className="text-lg font-semibold text-foreground">{title}</h1>

              {subtitle && (
                <p className="text-xs text-muted-foreground">{subtitle}</p>
              )}
            </div>
          </div>

          {/* User profile area and profile dropdown menu. */}
          <div className="flex items-center gap-4">
            <div className="relative" ref={profileMenuRef}>
              {/* Profile button opens and closes the user menu. */}
              <button
                type="button"
                onClick={() => setProfileMenuOpen((open) => !open)}
                className="flex items-center gap-3 rounded-lg p-1.5 text-left transition-colors hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring/30"
                aria-haspopup="menu"
                aria-expanded={profileMenuOpen}
                aria-label="Open profile menu"
              >
                {/* User name and email shown beside the avatar on larger screens. */}
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

                {/* Firebase profile photo, with initials used as a fallback. */}
                {profilePhotoUrl ? (
                  <img
                    src={profilePhotoUrl}
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
                    profilePhotoUrl ? "hidden" : ""
                  }`}
                  aria-label={profileName}
                >
                  {initials}
                </div>
              </button>

              {/* Profile dropdown with dashboard navigation and logout. */}
              {profileMenuOpen && (
                <div
                  role="menu"
                  className="absolute right-0 top-full z-50 mt-2 w-64 overflow-hidden rounded-xl border border-border bg-card p-2 shadow-lg"
                >
                  {/* Expanded profile information shown at the top of the menu. */}
                  <div className="border-b border-border px-3 py-2.5">
                    <div className="truncate text-sm font-semibold text-foreground">
                      {profileName}
                    </div>
                    {profileEmail && (
                      <div className="mt-0.5 truncate text-xs text-muted-foreground">
                        {profileEmail}
                      </div>
                    )}
                  </div>

                  {/* Quick link back to the dashboard. */}
                  <Link
                    to="/dashboard"
                    role="menuitem"
                    onClick={() => setProfileMenuOpen(false)}
                    className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-foreground hover:bg-muted"
                  >
                    <LayoutDashboard className="h-4 w-4" />
                    Dashboard - test
                  </Link>

                  {/* Logout action inside the profile menu. */}
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => void handleLogout()}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-destructive hover:bg-destructive/10"
                  >
                    <LogOut className="h-4 w-4" />
                    Logout
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Main content area where Dashboard, Upload, Results, or Reports are rendered. */}
        <main className="flex-1 overflow-auto p-8">{children}</main>
      </div>
    </div>
  );
}
