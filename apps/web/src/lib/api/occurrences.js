const API_BASE_URL_ERROR = "Missing public API base URL.";

function getApiBaseUrl() {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
  if (!apiBaseUrl) {
    throw new Error(API_BASE_URL_ERROR);
  }
  return apiBaseUrl;
}

function buildHeaders(accessToken, organizationId) {
  if (!accessToken) {
    throw new Error("Missing Supabase access token.");
  }
  if (!organizationId) {
    throw new Error("Missing active organization.");
  }

  return {
    Authorization: `Bearer ${accessToken}`,
    "X-Organization-Id": organizationId,
  };
}

export class OccurrencesRequestError extends Error {
  constructor(status, payload) {
    super("Occurrences request failed.");
    this.name = "OccurrencesRequestError";
    this.status = status;
    this.payload = payload;
  }
}

export async function fetchOccurrences(
  { accessToken, organizationId, status, query, page = 1, pageSize = 20 },
  fetchImpl = fetch,
) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (status) {
    params.set("status", status);
  }
  if (query) {
    params.set("q", query);
  }

  const response = await fetchImpl(`${getApiBaseUrl()}/occurrences?${params.toString()}`, {
    method: "GET",
    headers: buildHeaders(accessToken, organizationId),
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new OccurrencesRequestError(response.status, payload);
  }

  return payload;
}
