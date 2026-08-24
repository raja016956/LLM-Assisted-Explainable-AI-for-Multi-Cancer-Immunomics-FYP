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
  const result = await signInWithPopup(auth, googleProvider);

  await createOrUpdateUserProfile(result.user);

  return result;
}

export async function signInWithEmail(
  email: string,
  password: string,
): Promise<UserCredential> {
  const result = await signInWithEmailAndPassword(
    auth,
    email,
    password,
  );

  await createOrUpdateUserProfile(result.user);

  return result;
}

export async function resetPassword(
  email: string,
): Promise<void> {
  await sendPasswordResetEmail(auth, email);
}

export async function logout(): Promise<void> {
  await signOut(auth);
}