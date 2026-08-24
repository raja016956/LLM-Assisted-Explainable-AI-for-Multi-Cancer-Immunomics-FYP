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

const googleProvider = new GoogleAuthProvider();

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

export async function resetPassword(email: string): Promise<void> {
  await sendPasswordResetEmail(auth, email);
}

export async function logout(): Promise<void> {
  await signOut(auth);
}