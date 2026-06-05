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

async function parseResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new OccurrencesRequestError(response.status, payload);
  }
  return payload;
}

export async function fetchOccurrenceDetail(
  { occurrenceId, accessToken, organizationId },
  fetchImpl = fetch,
) {
  if (!occurrenceId) {
    throw new Error("Missing occurrence id.");
  }

  const response = await fetchImpl(`${getApiBaseUrl()}/occurrences/${occurrenceId}`, {
    method: "GET",
    headers: buildHeaders(accessToken, organizationId),
  });

  return parseResponse(response);
}

export async function fetchOccurrenceFields(
  { occurrenceId, accessToken, organizationId },
  fetchImpl = fetch,
) {
  if (!occurrenceId) {
    throw new Error("Missing occurrence id.");
  }

  const response = await fetchImpl(`${getApiBaseUrl()}/occurrences/${occurrenceId}/fields`, {
    method: "GET",
    headers: buildHeaders(accessToken, organizationId),
  });

  return parseResponse(response);
}

export async function updateOccurrenceField(
  { occurrenceId, fieldId, accessToken, organizationId, value, justification },
  fetchImpl = fetch,
) {
  if (!occurrenceId || !fieldId) {
    throw new Error("Missing occurrence field target.");
  }

  const response = await fetchImpl(
    `${getApiBaseUrl()}/occurrences/${occurrenceId}/fields/${fieldId}`,
    {
      method: "PATCH",
      headers: {
        ...buildHeaders(accessToken, organizationId),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ value, justification }),
    },
  );

  return parseResponse(response);
}

export async function approveOccurrenceField(
  { occurrenceId, fieldId, accessToken, organizationId, justification },
  fetchImpl = fetch,
) {
  if (!occurrenceId || !fieldId) {
    throw new Error("Missing occurrence field target.");
  }

  const response = await fetchImpl(
    `${getApiBaseUrl()}/occurrences/${occurrenceId}/fields/${fieldId}/approve`,
    {
      method: "POST",
      headers: {
        ...buildHeaders(accessToken, organizationId),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ justification }),
    },
  );

  return parseResponse(response);
}
