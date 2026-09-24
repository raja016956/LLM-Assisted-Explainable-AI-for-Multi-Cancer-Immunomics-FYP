import {
  GoogleAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  sendPasswordResetEmail,
  signOut,
  type UserCredential,
} from "firebase/auth";

import { auth } from "./firebase";
import { createOrUpdateUserProfile } from "./firestore";

// Google provider used by the "Continue with Google" button.
const googleProvider = new GoogleAuthProvider();

// Google authentication flow: opens the Firebase popup, saves the user profile, and returns the Firebase credential.
export async function signInWithGoogle(): Promise<UserCredential> {
  try {
    console.log("[Firebase Auth] Starting Google sign-in");
    console.log("[Firebase Auth] authDomain:", auth.config.authDomain);
    console.log("[Firebase Auth] projectId:", auth.config.projectId);
    console.log("[Firebase Auth] current origin:", window.location.origin);

    const result = await signInWithPopup(auth, googleProvider);

    console.log("[Firebase Auth] Google sign-in successful");
    console.log("[Firebase Auth] user:", result.user.email);

    await createOrUpdateUserProfile(result.user);

    return result;
  } catch (error: unknown) {
    console.error("[Firebase Auth] Google sign-in failed:", error);

    if (error instanceof Error) {
      console.error("[Firebase Auth] error message:", error.message);
    }

    if (typeof error === "object" && error !== null && "code" in error) {
      console.error(
        "[Firebase Auth] error code:",
        (error as { code?: string }).code,
      );
    }

    throw error;
  }
}

// Email/password authentication flow used by the sign-in form.
export async function signInWithEmail(
  email: string,
  password: string,
): Promise<UserCredential> {
  try {
    const result = await signInWithEmailAndPassword(
      auth,
      email,
      password,
    );

    await createOrUpdateUserProfile(result.user);

    return result;
  } catch (error) {
    console.error("[Firebase Auth] Email sign-in failed:", error);
    throw error;
  }
}

// Sends Firebase's password-reset email to the supplied address.
export async function resetPassword(email: string): Promise<void> {
  await sendPasswordResetEmail(auth, email);
}

// Signs the current Firebase user out of the application.
export async function logout(): Promise<void> {
  await signOut(auth);
}