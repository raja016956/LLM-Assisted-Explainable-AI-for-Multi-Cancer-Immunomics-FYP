import { doc, serverTimestamp, setDoc } from "firebase/firestore";
import type { User } from "firebase/auth";

import { db } from "./firebase";

// Creates or updates the signed-in user profile in Firestore using the Firebase UID as the document ID.
export async function createOrUpdateUserProfile(
  user: User,
): Promise<void> {
  // The UID keeps each profile tied to the authenticated Firebase account.
  const userRef = doc(db, "users", user.uid);

  await setDoc(
    userRef,
    {
      uid: user.uid,
      fullName: user.displayName ?? "",
      email: user.email ?? "",
      photoUrl: user.photoURL ?? "",
      provider: user.providerData[0]?.providerId ?? "password",
      updatedAt: serverTimestamp(),
    },
    {
      merge: true,
    },
  );
}