import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

// Firebase configuration is read from Vite environment variables so configuration is not hard-coded in components.
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

// Initialize Firebase once and share its services throughout the frontend.
const app = initializeApp(firebaseConfig);

// Firebase Authentication: manages Google and email/password sign-in and the current user session.
export const auth = getAuth(app);
// Firestore: stores user profile information associated with the Firebase UID.
export const db = getFirestore(app);

export default app;