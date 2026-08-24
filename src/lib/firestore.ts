import { doc, serverTimestamp, setDoc } from "firebase/firestore";
import type { User } from "firebase/auth";

import { db } from "./firebase";

export async function createOrUpdateUserProfile(
  user: User,
): Promise<void> {
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