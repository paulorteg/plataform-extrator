import { fetchAuthMe } from "../api/auth-me.js";
import { getSupabaseClient } from "../supabase/client.js";

export async function signInWithSupabase(email, password) {
  return getSupabaseClient().auth.signInWithPassword({ email, password });
}

export async function signOutFromSupabase() {
  return getSupabaseClient().auth.signOut();
}

export async function getSupabaseSession() {
  const { data, error } = await getSupabaseClient().auth.getSession();
  if (error) {
    throw error;
  }
  return data.session;
}

export async function loadCurrentUser(fetchImpl = fetch) {
  const session = await getSupabaseSession();
  const accessToken = session?.access_token;
  if (!accessToken) {
    return null;
  }
  return fetchAuthMe(accessToken, fetchImpl);
}
