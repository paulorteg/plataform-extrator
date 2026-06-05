function getApiBaseUrl() {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
  if (!apiBaseUrl) {
    throw new Error("Missing public API base URL.");
  }
  return apiBaseUrl;
}

export class AuthMeRequestError extends Error {
  constructor(status, payload) {
    super("Failed to load authenticated user.");
    this.name = "AuthMeRequestError";
    this.status = status;
    this.payload = payload;
  }
}

export async function fetchAuthMe(accessToken, fetchImpl = fetch) {
  if (!accessToken) {
    throw new Error("Missing Supabase access token.");
  }

  const response = await fetchImpl(`${getApiBaseUrl()}/auth/me`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new AuthMeRequestError(response.status, payload);
  }

  return payload;
}
