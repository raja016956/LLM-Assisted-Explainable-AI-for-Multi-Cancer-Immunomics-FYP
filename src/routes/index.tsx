import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Dna, Mail, Lock, ShieldCheck, Loader2 } from "lucide-react";

import {
  signInWithGoogle,
  signInWithEmail,
  resetPassword,
} from "@/lib/auth";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Sign in — ImmunoXAI" },
      {
        name: "description",
        content:
          "Sign in to ImmunoXAI, an LLM-assisted explainable AI platform for multi-cancer immunomics research.",
      },
      { property: "og:title", content: "Sign in — ImmunoXAI" },
      {
        property: "og:description",
        content: "Explainable AI for multi-cancer immunomics research.",
      },
    ],
  }),
  component: Login,
});

// Sign-in page: provides Google and email/password authentication and routes successful sign-ins to the Dashboard.
function Login() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // Starts Firebase Google authentication from the "Continue with Google" button.
  async function handleGoogleSignIn() {
    setError("");
    setMessage("");
    setGoogleLoading(true);

    try {
      console.log("========================================");
      console.log("[ImmunoXAI] Google sign-in started");
      console.log("[ImmunoXAI] Current URL:", window.location.href);
      console.log("[ImmunoXAI] Current origin:", window.location.origin);
      console.log("========================================");

      const result = await signInWithGoogle();

      console.log("[ImmunoXAI] Google authentication successful");
      console.log("[ImmunoXAI] User:", result.user.email);
      console.log("[ImmunoXAI] UID:", result.user.uid);

      await navigate({ to: "/dashboard" });
    } catch (err: unknown) {
      console.error("========================================");
      console.error("[ImmunoXAI] Google sign-in FAILED");
      console.error("[ImmunoXAI] Full error:", err);

      if (err instanceof Error) {
        console.error("[ImmunoXAI] Error message:", err.message);
        console.error("[ImmunoXAI] Error stack:", err.stack);
      }

      if (typeof err === "object" && err !== null && "code" in err) {
        console.error(
          "[ImmunoXAI] Firebase error code:",
          (err as { code?: unknown }).code,
        );
      }

      console.error("========================================");

      setError(getAuthErrorMessage(err));
    } finally {
      setGoogleLoading(false);
    }
  }

  // Submits the email/password form to Firebase Authentication.
  async function handleEmailSignIn(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError("");
    setMessage("");
    setLoading(true);

    try {
      console.log("[ImmunoXAI] Email sign-in started");

      const result = await signInWithEmail(email, password);

      console.log("[ImmunoXAI] Email authentication successful");
      console.log("[ImmunoXAI] User:", result.user.email);

      await navigate({ to: "/dashboard" });
    } catch (err: unknown) {
      console.error("[ImmunoXAI] Email sign-in failed:", err);

      setError(getAuthErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  // Sends a Firebase password-reset email using the address entered in the form.
  async function handleForgotPassword() {
    setError("");
    setMessage("");

    if (!email) {
      setError("Please enter your email address first.");
      return;
    }

    try {
      await resetPassword(email);

      setMessage(
        "Password reset email sent. Please check your inbox.",
      );
    } catch (err: unknown) {
      console.error("[ImmunoXAI] Password reset failed:", err);

      setError(getAuthErrorMessage(err));
    }
  }

  return (
    <div className="grid min-h-screen w-full grid-cols-1 lg:grid-cols-2">
      {/* Left brand panel */}
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-primary via-primary to-[oklch(0.35_0.16_260)] p-12 text-primary-foreground lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/15 backdrop-blur">
            <Dna className="h-5 w-5" />
          </div>

          <div>
            <div className="text-sm font-semibold">ImmunoXAI</div>
            <div className="text-xs text-white/70">
              Immunomics Platform
            </div>
          </div>
        </div>

        <div className="relative z-10 max-w-md">
          <h2 className="text-3xl font-semibold leading-tight">
            LLM-Assisted Explainable AI for Multi-Cancer Immunomics.
          </h2>

          <p className="mt-4 text-sm text-white/80">
            Interpret tumor immune phenotypes with transparent SHAP
            explanations grounded in curated biomedical literature —
            across BRCA, LUAD, COAD, SKCM, and GBM cohorts.
          </p>

          <div className="mt-8 grid grid-cols-3 gap-3 text-xs">
            {[
              { k: "12,480", v: "Samples analyzed" },
              { k: "5", v: "Cancer types" },
              { k: "94.6%", v: "Mean model AUC" },
            ].map((s) => (
              <div
                key={s.v}
                className="rounded-lg border border-white/15 bg-white/5 p-3"
              >
                <div className="text-lg font-semibold">{s.k}</div>
                <div className="mt-0.5 text-white/70">{s.v}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-white/70">
          <ShieldCheck className="h-4 w-4" />
          HIPAA-aware · TCGA compatible · Read-only PHI
        </div>

        <div className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full border border-white/10" />

        <div className="pointer-events-none absolute -bottom-40 -right-10 h-[28rem] w-[28rem] rounded-full border border-white/10" />
      </div>

      {/* Right form panel */}
      <div className="flex items-center justify-center bg-background p-8">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2 lg:hidden">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Dna className="h-5 w-5" />
            </div>

            <span className="font-semibold">ImmunoXAI</span>
          </div>

          <h1 className="text-2xl font-semibold text-foreground">
            Welcome back
          </h1>

          <p className="mt-1 text-sm text-muted-foreground">
            Sign in to continue your immunomics analysis.
          </p>

          {/* Google Sign In */}
          <button
            type="button"
            onClick={handleGoogleSignIn}
            disabled={googleLoading || loading}
            className="mt-8 flex h-11 w-full items-center justify-center gap-3 rounded-lg border border-border bg-card text-sm font-medium text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
          >
            {googleLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <GoogleIcon />
            )}

            {googleLoading
              ? "Signing in..."
              : "Continue with Google"}
          </button>

          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />

            <span className="text-xs uppercase tracking-wider text-muted-foreground">
              or
            </span>

            <div className="h-px flex-1 bg-border" />
          </div>

          {/* Error message */}
          {error && (
            <div className="mb-4 rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-xs text-destructive">
              {error}
            </div>
          )}

          {/* Success message */}
          {message && (
            <div className="mb-4 rounded-lg border border-primary/20 bg-primary/10 px-3 py-2 text-xs text-primary">
              {message}
            </div>
          )}

          {/* Email/password form */}
          <form
            className="space-y-4"
            onSubmit={handleEmailSignIn}
          >
            <div>
              <label className="text-xs font-medium text-foreground">
                Email
              </label>

              <div className="relative mt-1.5">
                <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />

                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="researcher@lab.edu"
                  className="h-11 w-full rounded-lg border border-input bg-background pl-10 pr-3 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/20"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-foreground">
                  Password
                </label>

                <button
                  type="button"
                  onClick={handleForgotPassword}
                  className="text-xs text-primary hover:underline"
                >
                  Forgot?
                </button>
              </div>

              <div className="relative mt-1.5">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />

                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="h-11 w-full rounded-lg border border-input bg-background pl-10 pr-3 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/20"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || googleLoading}
              className="flex h-11 w-full items-center justify-center rounded-lg bg-primary text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            New to ImmunoXAI?{" "}
            <Link
              to="/dashboard"
              className="font-medium text-primary hover:underline"
            >
              Request lab access
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

// Converts Firebase authentication error codes into readable messages shown on the page.
function getAuthErrorMessage(error: unknown): string {
  if (
    typeof error === "object" &&
    error !== null &&
    "code" in error
  ) {
    const code = String(
      (error as { code?: unknown }).code ?? "",
    );

    switch (code) {
      case "auth/invalid-credential":
        return "The email or password is incorrect.";

      case "auth/user-not-found":
        return "No account was found with this email.";

      case "auth/wrong-password":
        return "The password is incorrect.";

      case "auth/invalid-email":
        return "Please enter a valid email address.";

      case "auth/popup-closed-by-user":
        return "Google sign-in was cancelled.";

      case "auth/popup-blocked":
        return "Your browser blocked the Google sign-in popup. Please allow popups and try again.";

      case "auth/cancelled-popup-request":
        return "The Google sign-in request was cancelled.";

      case "auth/network-request-failed":
        return "Network error. Please check your internet connection.";

      case "auth/too-many-requests":
        return "Too many attempts. Please wait a while and try again.";

      case "auth/unauthorized-domain":
        return "Firebase rejected this website domain. Check Firebase Authentication → Settings → Authorized domains.";

      case "auth/operation-not-allowed":
        return "Google sign-in is not enabled in Firebase Authentication.";

      case "auth/account-exists-with-different-credential":
        return "An account already exists with a different sign-in method.";

      case "auth/internal-error":
        return "Firebase returned an internal authentication error. Check the browser console for details.";

      default: {
        const message =
          error instanceof Error
            ? error.message
            : String(error);

        return `Firebase authentication error (${code || "unknown"}): ${message}`;
      }
    }
  }

  if (error instanceof Error) {
    return `Authentication error: ${error.message}`;
  }

  return `Authentication error: ${String(error)}`;
}

// Inline Google icon used by the Google sign-in button.
function GoogleIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 48 48"
      aria-hidden="true"
    >
      <path
        fill="#FFC107"
        d="M43.6 20.5H42V20H24v8h11.3C33.7 32.5 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.3 6.1 29.4 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.2-.1-2.3-.4-3.5z"
      />

      <path
        fill="#FF3D00"
        d="M6.3 14.7l6.6 4.8C14.7 15.4 19 12 24 12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.3 6.1 29.4 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"
      />

      <path
        fill="#4CAF50"
        d="M24 44c5.3 0 10.1-2 13.7-5.3l-6.3-5.3C29.2 34.9 26.7 36 24 36c-5.3 0-9.7-3.4-11.3-8.1l-6.5 5C9.5 39.6 16.2 44 24 44z"
      />

      <path
        fill="#1976D2"
        d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.3 4.3-4.2 5.7l6.3 5.3C41.3 35.4 44 30.1 44 24c0-1.2-.1-2.3-.4-3.5z"
      />
    </svg>
  );
}